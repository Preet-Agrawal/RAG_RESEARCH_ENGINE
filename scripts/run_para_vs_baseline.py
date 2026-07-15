#!/usr/bin/env python3
"""
Multi-run, multi-position PARA vs. baseline comparison.

Purpose: get a real, defensible headline percentage for "does PARA (the full
system: semantic chunking + multi-granularity retrieval + cross-encoder
rerank + position-bias correction) solve lost-in-the-middle better than no
mitigation" -- with enough repeated trials to survive "how many runs was
that?" in an interview. This is deliberately NOT the adversarially-engineered
document from the rescue experiment; it's a plain needle-in-haystack test on
an untouched real PDF, run multiple times per cell for variance.

This measures the SYSTEM, not the position-correction term in isolation --
see PARA_EMPIRICAL_FINDINGS.md and the rescue-experiment scripts for that
narrower, harder question.
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

from process_pdf import extract_text_from_pdf, answer_question
from src.core.llm_client import _is_rate_limit_error

PDF_PATH = PROJECT_ROOT / "data" / "uploads" / "1783412814023_Object Oriented Programmings.pdf"
POSITIONS = [0.1, 0.5, 0.9]
NUM_RUNS = 3
STRATEGIES = ["baseline", "para"]

NEEDLE_FACT = ("According to the Kirchner benchmark, virtual function dispatch "
               "adds 7 nanoseconds of overhead per call.")
NEEDLE_QUESTION = ("According to the Kirchner benchmark, how many nanoseconds "
                    "of overhead does virtual function dispatch add per call?")

CALL_DELAY_SEC = 2.0
RATE_LIMIT_RETRY_DELAY_SEC = 15.0
RETRY_DELAY_SEC = 5.0


def insert_needle(text: str, position: float) -> str:
    words = text.split()
    idx = int(len(words) * position)
    return " ".join(words[:idx] + [f"\n\n{NEEDLE_FACT}\n\n"] + words[idx:])


def found_needle(answer: str) -> bool:
    ans = (answer or "").lower()
    return "7 nanosecond" in ans or "7ns" in ans or ("kirchner" in ans and "7" in ans)


def run_cell(pdf_text: str, strategy: str, position: float, run_idx: int) -> dict:
    modified = insert_needle(pdf_text, position)
    attempt = 0
    while True:
        attempt += 1
        try:
            t0 = time.time()
            result = answer_question(modified, NEEDLE_QUESTION, strategy=strategy, provider="groq")
            if result.get("error"):
                raise RuntimeError(result["error"])
            answer = result.get("answer", "")
            return {
                "strategy": strategy, "position": position, "run": run_idx,
                "ok": True, "found": found_needle(answer),
                "answer_sample": answer[:250],
                "latency": round(time.time() - t0, 2),
                "model_used": result.get("model_used"),
            }
        except Exception as e:
            if attempt == 1:
                delay = RATE_LIMIT_RETRY_DELAY_SEC if _is_rate_limit_error(e) else RETRY_DELAY_SEC
                print(f"      [retry after {delay}s] {type(e).__name__}: {e}")
                time.sleep(delay)
                continue
            return {
                "strategy": strategy, "position": position, "run": run_idx,
                "ok": False, "error": f"{type(e).__name__}: {e}",
            }


def main():
    print(f"-> Extracting {PDF_PATH.name}...")
    pdf_text = extract_text_from_pdf(str(PDF_PATH))
    assert "kirchner" not in pdf_text.lower()
    print(f"   {len(pdf_text.split())} words\n")

    total_calls = len(STRATEGIES) * len(POSITIONS) * NUM_RUNS
    print(f"Strategies: {STRATEGIES}  Positions: {POSITIONS}  Runs/cell: {NUM_RUNS}  "
          f"Total calls: {total_calls}\n")

    all_results = []
    for strategy in STRATEGIES:
        for position in POSITIONS:
            found_flags = []
            for run_idx in range(NUM_RUNS):
                r = run_cell(pdf_text, strategy, position, run_idx)
                all_results.append(r)
                if r["ok"]:
                    found_flags.append(r["found"])
                    print(f"  [{strategy:8s} pos={position:.1f} run={run_idx+1}/{NUM_RUNS}] "
                          f"found={r['found']}  latency={r['latency']}s")
                else:
                    print(f"  [{strategy:8s} pos={position:.1f} run={run_idx+1}/{NUM_RUNS}] FAILED: {r['error']}")
                time.sleep(CALL_DELAY_SEC)
            rate = sum(found_flags) / len(found_flags) if found_flags else None
            rate_str = f"{rate:.0%}" if rate is not None else "n/a"
            print(f"    -> {strategy} @ pos={position}: {sum(found_flags)}/{len(found_flags)} found ({rate_str})")
            print()

    # Aggregate
    summary = {}
    for strategy in STRATEGIES:
        cells = [r for r in all_results if r["strategy"] == strategy and r["ok"]]
        middle_cells = [r for r in cells if r["position"] == 0.5]
        overall_rate = sum(1 for r in cells if r["found"]) / len(cells) if cells else None
        middle_rate = sum(1 for r in middle_cells if r["found"]) / len(middle_cells) if middle_cells else None
        n_failed = sum(1 for r in all_results if r["strategy"] == strategy and not r["ok"])
        summary[strategy] = {
            "overall_accuracy": overall_rate,
            "middle_accuracy": middle_rate,
            "n_ok": len(cells),
            "n_failed": n_failed,
        }

    print("=== SUMMARY ===")
    for strategy, s in summary.items():
        print(f"{strategy:10s}  overall={s['overall_accuracy']:.0%}  middle={s['middle_accuracy']:.0%}  "
              f"(n_ok={s['n_ok']}, n_failed={s['n_failed']})")

    out_dir = PROJECT_ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"para_vs_baseline_{ts}.json"
    out_file.write_text(json.dumps({
        "pdf": str(PDF_PATH), "positions": POSITIONS, "num_runs": NUM_RUNS,
        "strategies": STRATEGIES, "needle_fact": NEEDLE_FACT, "needle_question": NEEDLE_QUESTION,
        "results": all_results, "summary": summary,
    }, indent=2))
    print(f"\n[OK] Saved: {out_file}")


if __name__ == "__main__":
    main()
