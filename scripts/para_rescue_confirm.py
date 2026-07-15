#!/usr/bin/env python3
"""
Full-pipeline confirmation of the rescue case found by para_rescue_diagnostic.py:
needle ranks #13/1671 by semantic score alone (outside top_k=10 -> never
selected for context) but #1/1671 once PARA's position correction is applied.

This calls the real generation pipeline twice, on the identical constructed
document and question:
  1. strategy="para" via the real, unmodified answer_question() — production
     defaults, position correction ON.
  2. The same apply_para() call with correction_type="none" (position
     correction OFF, everything else identical) — built the same way
     answer_question()'s own "para" branch builds its prompt, so the only
     variable that changes between the two calls is the correction term.

Two real Groq calls (not many more — the diagnostic already did the free,
non-LLM ranking measurement). Confirms the ranking-level finding actually
changes the real generated answer, not just an internal score.
"""
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from process_pdf import extract_text_from_pdf, answer_question, get_llm_client, MiddleRecoveryProcessor
from para_rescue_diagnostic import build_document, QUESTION, PDF_PATH

FOUND_MARKER = "7 nanosecond"


def found(answer: str) -> bool:
    return FOUND_MARKER in (answer or "").lower()


def main():
    print(f"-> Loading {PDF_PATH.name}...")
    base_text = extract_text_from_pdf(str(PDF_PATH))
    doc = build_document(base_text)
    print(f"   doc: {len(doc.split())} words\n")

    # ---- Condition 1: real, unmodified strategy="para" (position correction ON, production defaults) ----
    print("=== Condition 1: full PARA (production defaults, correction ON) ===")
    t0 = time.time()
    result_on = answer_question(doc, QUESTION, strategy="para", provider="groq")
    print(f"  answer: {result_on['answer'][:300]!r}")
    print(f"  correct={found(result_on['answer'])}  confidence={result_on.get('confidence')}  "
          f"latency={time.time()-t0:.1f}s  model={result_on.get('model_used')}\n")

    # ---- Condition 2: identical setup, correction_type="none" (position correction OFF) ----
    print("=== Condition 2: same setup, correction_type='none' (correction OFF) ===")
    client = get_llm_client("groq")
    processor = MiddleRecoveryProcessor(client)
    chunks = processor.chunk_text_semantic(doc)

    # NOTE: correction_type="none" alone is NOT sufficient here.
    # retrieve_multi_granularity() (src/para.py:444) never passes
    # correction_type through to its internal score_chunks() call, so it
    # silently keeps using score_chunks()'s own default ("sin") regardless
    # of what's requested here -- a real gap, verified by reading the code,
    # not assumed. beta *does* multiply through unconditionally in the final
    # score formula (alpha*sem + beta*pos_corr), so beta=0.0 is what actually
    # zeroes the correction's contribution end-to-end, including inside the
    # multi-granularity path. Both are passed for clarity; beta=0.0 is the
    # one doing the real work.
    t0 = time.time()
    context, sem_conf = processor.apply_para(
        chunks, QUESTION, full_text=doc, correction_type="none", beta=0.0,
    )
    if len(context) > 24000:
        context = context[:24000]
    prompt = (f"{context}\n\n---\nBased ONLY on the retrieved sections above, "
              f"provide a DETAILED and COMPREHENSIVE answer.\n\nQuestion: {QUESTION}\n\nDetailed Answer:")
    response = client.generate(prompt, system_prompt=processor.get_system_prompt("para"))
    print(f"  answer: {response.text[:300]!r}")
    print(f"  correct={found(response.text)}  semantic_confidence={sem_conf:.4f}  "
          f"latency={time.time()-t0:.1f}s  model={client.model}\n")

    print("=== Summary ===")
    print(f"  correction ON  : correct={found(result_on['answer'])}")
    print(f"  correction OFF : correct={found(response.text)}")


if __name__ == "__main__":
    main()
