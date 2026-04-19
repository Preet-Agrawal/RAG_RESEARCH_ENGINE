#!/usr/bin/env python3
"""
PARA ablation experiment runner.

Runs the key ablations needed to answer reviewer objections 2 and 3:

  OBJ-2: Correction function is arbitrary.
    → Sweep correction_type ∈ {sin, gaussian, step, triangle, none}
      with all other PARA components fixed.

  OBJ-3: Cross-encoder is doing the work.
    → Run the 2×2 factorial:
      (bi-encoder only) vs (+ position correction)
      × (no rerank) vs (+ cross-encoder)
      = 4 configs. Report marginal gain of correction in each.

Protocol:
  - Takes a PDF and a question list (one per line)
  - Uses a needle-in-the-haystack probe (default) OR direct QA
  - Runs each config on each question
  - Outputs per-config metrics: needle-found rate, latency, semantic score
  - Saves JSON to results/ablation_<timestamp>.json

USAGE:
  python scripts/run_ablation.py \\
      --pdf data/uploads/paper.pdf \\
      --questions questions.txt \\
      --experiment correction_function \\
      --num-runs 1

  python scripts/run_ablation.py \\
      --pdf data/uploads/paper.pdf \\
      --experiment cross_encoder \\
      --num-runs 3
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from process_pdf import (
    extract_text_from_pdf,
    get_llm_client,
    MiddleRecoveryProcessor,
    PARA_AVAILABLE,
)


# ── Experiment definitions ──────────────────────────────────────────────────


def exp_correction_function() -> List[Dict[str, Any]]:
    """OBJ-2: Ablate the correction function. Everything else held constant."""
    base = {
        "alpha": 0.7,
        "beta": 0.3,
        "adaptive_gamma": True,
        "use_cross_encoder": True,
        "use_multi_granularity": True,
    }
    return [
        {**base, "name": "sin (ours)",   "correction_type": "sin"},
        {**base, "name": "gaussian",     "correction_type": "gaussian"},
        {**base, "name": "triangle",     "correction_type": "triangle"},
        {**base, "name": "step",         "correction_type": "step"},
        {**base, "name": "none",         "correction_type": "none", "beta": 0.0},
    ]


def exp_cross_encoder_factorial() -> List[Dict[str, Any]]:
    """OBJ-3: 2×2 factorial isolating position correction from cross-encoder."""
    base = {
        "alpha": 0.7,
        "adaptive_gamma": True,
        "use_multi_granularity": False,  # held OFF for a cleaner 2x2
    }
    return [
        # Bi-encoder only, no position correction (semantic baseline)
        {**base, "name": "semantic-only (baseline)", "beta": 0.0,
         "correction_type": "none", "use_cross_encoder": False},
        # Bi-encoder + position correction
        {**base, "name": "+ position correction", "beta": 0.3,
         "correction_type": "sin", "use_cross_encoder": False},
        # Bi-encoder + cross-encoder (no position)
        {**base, "name": "+ cross-encoder", "beta": 0.0,
         "correction_type": "none", "use_cross_encoder": True},
        # Both (full PARA)
        {**base, "name": "+ both (full PARA)", "beta": 0.3,
         "correction_type": "sin", "use_cross_encoder": True},
    ]


def exp_component_stack() -> List[Dict[str, Any]]:
    """Incremental stacking: show marginal contribution of each component."""
    return [
        {"name": "1. semantic only", "alpha": 0.7, "beta": 0.0,
         "correction_type": "none", "use_cross_encoder": False,
         "use_multi_granularity": False, "adaptive_gamma": False},
        {"name": "2. + multi-granularity", "alpha": 0.7, "beta": 0.0,
         "correction_type": "none", "use_cross_encoder": False,
         "use_multi_granularity": True, "adaptive_gamma": False},
        {"name": "3. + cross-encoder", "alpha": 0.7, "beta": 0.0,
         "correction_type": "none", "use_cross_encoder": True,
         "use_multi_granularity": True, "adaptive_gamma": False},
        {"name": "4. + fixed position correction (γ=0.3)", "alpha": 0.7, "beta": 0.3,
         "correction_type": "sin", "use_cross_encoder": True,
         "use_multi_granularity": True, "adaptive_gamma": False},
        {"name": "5. + adaptive γ (full PARA)", "alpha": 0.7, "beta": 0.3,
         "correction_type": "sin", "use_cross_encoder": True,
         "use_multi_granularity": True, "adaptive_gamma": True},
    ]


EXPERIMENTS = {
    "correction_function": exp_correction_function,
    "cross_encoder": exp_cross_encoder_factorial,
    "component_stack": exp_component_stack,
}


# ── Needle probe ────────────────────────────────────────────────────────────


NEEDLE_FACT = "The secret code for the research project is ALPHA-7749-OMEGA."
NEEDLE_QUESTION = "What is the secret code for the research project?"


def insert_needle(pdf_text: str, position: float) -> str:
    """Insert the needle fact at the given normalized position (0..1)."""
    words = pdf_text.split()
    idx = int(len(words) * position)
    return " ".join(words[:idx] + [f"\n\n{NEEDLE_FACT}\n\n"] + words[idx:])


def found_needle(answer: str) -> bool:
    upper = (answer or "").upper()
    return "7749" in upper or "ALPHA-7749" in upper


# ── Single-config evaluator ─────────────────────────────────────────────────


def run_one_config(
    pdf_text: str,
    config: Dict[str, Any],
    positions: List[float],
    num_runs: int,
    provider: str,
) -> Dict[str, Any]:
    """Evaluate one PARA configuration across all needle positions × runs."""
    if not PARA_AVAILABLE:
        raise RuntimeError("PARA not available — install sentence-transformers")

    client = get_llm_client(provider)
    processor = MiddleRecoveryProcessor(client)

    # Flags that belong to apply_para() only
    para_kwargs = {k: v for k, v in config.items() if k in {
        "alpha", "beta", "gamma", "correction_type",
        "adaptive_gamma", "use_cross_encoder", "use_multi_granularity",
    }}

    per_position = []
    t0 = time.time()

    for pos in positions:
        run_found = []
        run_latency = []
        run_semantic = []

        for run_idx in range(num_runs):
            modified = insert_needle(pdf_text, pos)
            chunks = processor.chunk_text(modified, chunk_size=400, overlap=50)

            t_start = time.time()
            try:
                context, sem_sim = processor.apply_para(
                    chunks, NEEDLE_QUESTION, full_text=modified, **para_kwargs
                )
                if len(context) > 24000:
                    context = context[:24000]

                prompt = (
                    f"{context}\n\n---\nQuestion: {NEEDLE_QUESTION}\n"
                    "Answer directly. If the document does not contain the answer, say so:"
                )
                resp = client.generate(
                    prompt,
                    system_prompt=processor.get_system_prompt("para"),
                )
                answer_text = resp.text
            except Exception as e:
                answer_text = f"[ERROR] {e}"
                sem_sim = 0.0

            run_found.append(1 if found_needle(answer_text) else 0)
            run_latency.append(time.time() - t_start)
            run_semantic.append(float(sem_sim))

        per_position.append({
            "position": int(pos * 100),
            "zone": "beginning" if pos < 0.33 else ("middle" if pos < 0.67 else "end"),
            "found_rate": sum(run_found) / len(run_found),
            "latency_mean": sum(run_latency) / len(run_latency),
            "semantic_mean": sum(run_semantic) / len(run_semantic),
            "raw_found": run_found,
        })

    # Overall metrics
    all_found = [p["found_rate"] for p in per_position]
    middle_found = [p["found_rate"] for p in per_position if p["zone"] == "middle"]

    return {
        "config": config,
        "positions": per_position,
        "overall_accuracy": sum(all_found) / len(all_found) if all_found else 0.0,
        "middle_accuracy": sum(middle_found) / len(middle_found) if middle_found else 0.0,
        "total_time_sec": round(time.time() - t0, 1),
    }


# ── Main ────────────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser(
        description="PARA ablation runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--pdf", required=True, help="Path to PDF")
    ap.add_argument("--experiment", required=True, choices=list(EXPERIMENTS.keys()),
                    help="Which ablation to run")
    ap.add_argument("--positions", type=str, default="0.1,0.25,0.4,0.5,0.6,0.75,0.9",
                    help="Comma-separated needle positions (0..1)")
    ap.add_argument("--num-runs", type=int, default=1,
                    help="Number of runs per (config, position) — for variance")
    ap.add_argument("--provider", default="groq", choices=["groq", "gemini", "openai", "anthropic"],
                    help="LLM provider (uses auto-fallback chain)")
    ap.add_argument("--output-dir", default="results")
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        ap.error(f"PDF not found: {pdf_path}")

    print(f"→ Extracting text from {pdf_path.name}...")
    pdf_text = extract_text_from_pdf(str(pdf_path))
    if pdf_text.startswith("Error"):
        print(f"ERROR: {pdf_text}", file=sys.stderr)
        sys.exit(1)
    print(f"  Got {len(pdf_text.split())} words")

    configs = EXPERIMENTS[args.experiment]()
    positions = [float(p) for p in args.positions.split(",")]

    print(f"\n→ Running experiment: {args.experiment}")
    print(f"  Configs: {len(configs)}")
    print(f"  Positions: {[int(p*100) for p in positions]}%")
    print(f"  Runs per cell: {args.num_runs}")
    print(f"  Total LLM calls: {len(configs) * len(positions) * args.num_runs}")
    print(f"  Provider: {args.provider}\n")

    results = []
    for i, cfg in enumerate(configs):
        print(f"[{i+1}/{len(configs)}] {cfg.get('name', 'config')}")
        res = run_one_config(pdf_text, cfg, positions, args.num_runs, args.provider)
        print(f"    overall={res['overall_accuracy']:.2%}  "
              f"middle={res['middle_accuracy']:.2%}  "
              f"time={res['total_time_sec']}s")
        results.append(res)

    # Save JSON
    out_dir = PROJECT_ROOT / args.output_dir
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"ablation_{args.experiment}_{ts}.json"

    payload = {
        "experiment": args.experiment,
        "pdf": str(pdf_path),
        "provider": args.provider,
        "positions": positions,
        "num_runs": args.num_runs,
        "results": results,
    }
    out_file.write_text(json.dumps(payload, indent=2))
    print(f"\n✓ Saved: {out_file}")

    # Summary table
    print("\n=== SUMMARY ===")
    print(f"{'Config':40s}  {'Overall':>8s}  {'Middle':>8s}  {'Time':>6s}")
    print("-" * 68)
    for r in results:
        name = r["config"].get("name", "?")
        print(f"{name:40s}  {r['overall_accuracy']:>7.1%}   {r['middle_accuracy']:>7.1%}   {r['total_time_sec']:>5}s")


if __name__ == "__main__":
    main()
