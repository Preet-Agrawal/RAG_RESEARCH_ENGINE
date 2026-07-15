#!/usr/bin/env python3
"""
Cross-strategy needle-in-a-haystack benchmark.

Runs all 11 strategies in VALID_STRATEGIES against one identical setup —
same document, same needle fact, same insertion position, same question —
and records, per strategy, whether the needle actually reached the LLM and
whether the real completion states it correctly.

This does NOT call any private/duplicated logic to build prompts. It calls
the real, unmodified `answer_question()` — the same function the /ask
endpoint uses — for every strategy. The only instrumentation is a
non-invasive patch on `LLMClient.generate` that logs the prompt text of
every real call made during that strategy's run, so we can tell whether
the needle's text reached the model, without re-implementing or guessing
at each strategy's internal context-assembly logic.

For "para" only, an additional non-LLM diagnostic is run directly against
PARARetriever internals to report a true rank/pool-size (the only strategy
in this codebase with an actual top-k retrieval/selection step).

Every strategy is independently wrapped in a try/except. A strategy that
errors out (rate limit exhausted across the whole fallback chain, etc.) is
recorded with its raw error and excluded from the scored table — never
backfilled with a guessed result.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from process_pdf import extract_text_from_pdf, answer_question, MiddleRecoveryProcessor, PARA_AVAILABLE
from src.core.llm_client import LLMClient, _is_rate_limit_error

CALL_DELAY_SEC = 2.0
RATE_LIMIT_RETRY_DELAY_SEC = 15.0
RETRY_DELAY_SEC = 5.0

PDF_PATH = PROJECT_ROOT / "data" / "uploads" / "1783412814023_Object Oriented Programmings.pdf"
NEEDLE_POSITION = 0.5
NEEDLE_FACT = ("According to the Kirchner benchmark, virtual function dispatch "
               "adds 7 nanoseconds of overhead per call.")
NEEDLE_QUESTION = ("According to the Kirchner benchmark, how many nanoseconds "
                    "of overhead does virtual function dispatch add per call?")
NEEDLE_CHUNK_MARKER = "kirchner"  # unambiguous in document/chunk text (fine there)
# NOTE: NEEDLE_QUESTION itself also contains "kirchner", and every strategy's
# prompt template includes the question text — so "kirchner" is NOT a safe
# marker for "did the fact reach the LLM prompt" (it would false-positive on
# every single strategy, since the question is always in the prompt). Use a
# substring that appears ONLY in the fact sentence, never in the question.
NEEDLE_PROMPT_MARKER = "7 nanosecond"

STRATEGIES = [
    "baseline",
    "attention_anchoring",
    "relevance_restructuring",
    "query_aware_compression",
    "query_aware_contextualization",
    "reranking",
    "chunk_by_chunk_reasoning",
    "map_reduce",
    "chunked_reading",
    "combined",
    "para",
]


def insert_needle(text: str, position: float) -> str:
    words = text.split()
    idx = int(len(words) * position)
    return " ".join(words[:idx] + [f"\n\n{NEEDLE_FACT}\n\n"] + words[idx:])


def found_needle(answer: str) -> bool:
    ans = (answer or "").lower()
    return "7 nanosecond" in ans or "7ns" in ans or ("kirchner" in ans and "7" in ans)


class PromptLogger:
    """Patches LLMClient.generate for the duration of a `with` block and
    records every (prompt, system_prompt) pair actually sent to the LLM."""

    def __init__(self):
        self.calls = []
        self._orig = None

    def __enter__(self):
        self._orig = LLMClient.generate
        logger = self

        def patched(self_client, prompt, system_prompt=None, **kwargs):
            resp = logger._orig(self_client, prompt, system_prompt, **kwargs)
            logger.calls.append({
                "prompt_len": len(prompt),
                "contains_needle": NEEDLE_PROMPT_MARKER in prompt.lower(),
                "response_sample": resp.text[:200],
            })
            return resp

        LLMClient.generate = patched
        return self

    def __exit__(self, *exc):
        LLMClient.generate = self._orig


def run_para_rank_diagnostic(needle_text: str, question: str):
    """Non-LLM diagnostic: where does the needle chunk actually rank in
    PARA's candidate pools, at each granularity, under production defaults?
    No API call — this is a pure local embedding computation."""
    if not PARA_AVAILABLE:
        return {"error": "PARA not available"}

    from src.para import PARARetriever, multi_granularity_chunks, semantic_chunk_text

    retriever = PARARetriever()
    total_words = len(needle_text.split())

    diagnostics = {}

    # Top-level (semantic) chunks, as used by apply_para()'s own chunking step
    top_level_chunks = semantic_chunk_text(needle_text)
    scored_top = retriever.score_chunks(question, top_level_chunks, alpha=0.7, beta=0.3)
    scored_top.sort(key=lambda x: x[1], reverse=True)
    rank_top = next((i + 1 for i, s in enumerate(scored_top) if NEEDLE_CHUNK_MARKER in s[0].content.lower()), None)
    diagnostics["top_level"] = {
        "pool_size": len(scored_top),
        "needle_rank": rank_top,
        "in_top_10": (rank_top is not None and rank_top <= 10),
    }

    # Sentence-level pool (the granularity multi-granularity retrieval draws from)
    granularities = multi_granularity_chunks(needle_text, total_words)
    sentence_chunks = granularities.get("sentence", [])
    if sentence_chunks:
        scored_sent = retriever.score_chunks(question, sentence_chunks, alpha=0.7, beta=0.3)
        scored_sent.sort(key=lambda x: x[1], reverse=True)
        rank_sent = next((i + 1 for i, s in enumerate(scored_sent) if NEEDLE_CHUNK_MARKER in s[0].content.lower()), None)
        diagnostics["sentence_level"] = {
            "pool_size": len(scored_sent),
            "needle_rank": rank_sent,
            "in_top_10": (rank_sent is not None and rank_sent <= 10),
        }

    return diagnostics


def run_one_strategy(pdf_text: str, strategy: str) -> dict:
    attempt = 0
    while True:
        attempt += 1
        try:
            with PromptLogger() as logger:
                t0 = time.time()
                result = answer_question(pdf_text, NEEDLE_QUESTION, strategy=strategy, provider="groq")
                elapsed = time.time() - t0

            if result.get("error"):
                raise RuntimeError(result["error"])

            answer_text = result.get("answer", "")
            needle_in_any_prompt = any(c["contains_needle"] for c in logger.calls)

            return {
                "strategy": strategy,
                "ok": True,
                "answer_full": answer_text,
                "answer_sample": answer_text[:400],
                "correct": found_needle(answer_text),
                "needle_reached_llm": needle_in_any_prompt,
                "num_llm_calls": len(logger.calls),
                "chunks_processed": result.get("chunks_processed"),
                "strategy_used_actual": result.get("strategy_used"),  # catches fallback substitutions
                "latency_sec": round(elapsed, 2),
                "model_used": result.get("model_used"),
            }
        except Exception as e:
            if attempt == 1:
                delay = RATE_LIMIT_RETRY_DELAY_SEC if _is_rate_limit_error(e) else RETRY_DELAY_SEC
                print(f"    [retry after {delay}s] {type(e).__name__}: {e}")
                time.sleep(delay)
                continue
            return {
                "strategy": strategy,
                "ok": False,
                "error": f"{type(e).__name__}: {e}",
            }


def main():
    print(f"-> Extracting text from {PDF_PATH.name}...")
    pdf_text = extract_text_from_pdf(str(PDF_PATH))
    if pdf_text.startswith("Error"):
        print(f"ERROR: {pdf_text}", file=sys.stderr)
        sys.exit(1)
    print(f"   {len(pdf_text.split())} words, {len(pdf_text)} chars")

    assert NEEDLE_CHUNK_MARKER not in pdf_text.lower(), "Needle marker already present natively in source PDF!"
    assert NEEDLE_PROMPT_MARKER not in pdf_text.lower(), "Needle marker already present natively in source PDF!"

    modified_text = insert_needle(pdf_text, NEEDLE_POSITION)
    print(f"-> Needle inserted at position {NEEDLE_POSITION} "
          f"(word offset {int(len(pdf_text.split()) * NEEDLE_POSITION)})\n")

    results = []
    for i, strategy in enumerate(STRATEGIES):
        print(f"[{i+1}/{len(STRATEGIES)}] {strategy}")
        res = run_one_strategy(modified_text, strategy)
        if res["ok"]:
            print(f"    correct={res['correct']}  needle_reached_llm={res['needle_reached_llm']}  "
                  f"chunks={res['chunks_processed']}  calls={res['num_llm_calls']}  "
                  f"latency={res['latency_sec']}s")
        else:
            print(f"    FAILED: {res['error']}")
        results.append(res)
        time.sleep(CALL_DELAY_SEC)

    print("\n-> Running PARA rank/pool-size diagnostic (no LLM cost)...")
    para_diag = run_para_rank_diagnostic(modified_text, NEEDLE_QUESTION)
    print(f"   {para_diag}")

    out_dir = PROJECT_ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"strategy_benchmark_{ts}.json"
    payload = {
        "pdf": str(PDF_PATH),
        "needle_fact": NEEDLE_FACT,
        "needle_question": NEEDLE_QUESTION,
        "needle_position": NEEDLE_POSITION,
        "provider": "groq",
        "results": results,
        "para_rank_diagnostic": para_diag,
    }
    out_file.write_text(json.dumps(payload, indent=2))
    print(f"\n[OK] Saved: {out_file}")


if __name__ == "__main__":
    main()
