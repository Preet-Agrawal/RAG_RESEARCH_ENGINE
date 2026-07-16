#!/usr/bin/env python3
"""
Component-wise retrieval-rank ablation for PARA.

Measures retrieval quality DIRECTLY from the scoring pipeline (chunk rank,
not LLM-answer correctness) — no LLM calls, fully deterministic given fixed
model weights and fixed inputs. This isolates exactly two factors:

  - multi-granularity chunking  (sentence+paragraph+section pools, merged,
    vs. a single fixed-size 400-word/50-overlap chunk pool)
  - position-bias correction    (gamma * sin(pi * position) vs. none)

Conditions (2x2):
  FULL      = multi-granularity ON  + position correction ON
  ABLATE-A  = multi-granularity OFF + position correction ON
  ABLATE-B  = multi-granularity ON  + position correction OFF
  BASELINE  = multi-granularity OFF + position correction OFF

Cross-encoder reranking is held OFF in all four conditions — it is a third
component in src/para.py not named in this design, so it is excluded to
avoid confounding the two factors under test.

Rank definition: for each condition, the FULL uncapped candidate pool is
scored and sorted (no per-granularity-level cap, no top_k cap — see
src/para.py's retrieve_multi_granularity/build_para_context for the capped,
production version). "Needle chunk" = any candidate whose content contains
the needle fact verbatim; rank = 1-based position of the best (lowest-rank)
such candidate in the full sorted pool.

No LLM calls are made anywhere in this script.
"""

import csv
import random
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from process_pdf import extract_text_from_pdf, MiddleRecoveryProcessor
from src.core.llm_client import LLMClient  # only for MiddleRecoveryProcessor's constructor signature
from src.para import (
    PARARetriever,
    TextChunk as PARAChunk,
    multi_granularity_chunks,
    semantic_chunk_text,
)

SEED = 42
random.seed(SEED)

CORPUS_PATH = PROJECT_ROOT / "data" / "uploads" / "Cpp_repaired_trimmed_210pages.pdf"

NEEDLE_FACT = ("According to the Kirchner benchmark, virtual function dispatch "
               "adds 7 nanoseconds of overhead per call.")

QUERIES = [
    "According to the Kirchner benchmark, how many nanoseconds of overhead does virtual function dispatch add per call?",
    "What is the per-call overhead of virtual function dispatch according to the Kirchner benchmark?",
    "How much overhead in nanoseconds does virtual dispatch add, per the Kirchner benchmark?",
    "What did the Kirchner benchmark measure for virtual function call overhead?",
    "What is the nanosecond cost of a virtual function call per the Kirchner benchmark?",
    "According to Kirchner's benchmark results, what is the dispatch overhead of virtual functions?",
    "How many nanoseconds does each virtual function dispatch cost, based on Kirchner's benchmark?",
    "What overhead value did the Kirchner benchmark report for virtual dispatch?",
    "Per the Kirchner benchmark, what's the added latency of a virtual function call?",
    "What is the per-call nanosecond overhead figure from the Kirchner benchmark for virtual dispatch?",
    "Kirchner benchmark: how many nanoseconds per virtual function call?",
    "What overhead does calling a virtual function add, according to Kirchner's measurements?",
    "How costly, in nanoseconds, is virtual dispatch per the Kirchner benchmark?",
    "What does the Kirchner benchmark say about virtual function dispatch overhead?",
    "Find the nanosecond overhead of virtual function dispatch reported by the Kirchner benchmark.",
    "What's the measured overhead of virtual dispatch calls, Kirchner benchmark?",
    "How many extra nanoseconds does a virtual call take according to Kirchner?",
    "What is the Kirchner benchmark figure for virtual function call overhead in nanoseconds?",
    "Report the per-call overhead of virtual dispatch as measured by the Kirchner benchmark.",
    "According to Kirchner, what's the ns overhead added by each virtual function dispatch?",
    "What is the additional per-call cost of virtual function dispatch per the Kirchner benchmark?",
    "Kirchner's benchmark reports what overhead for virtual function dispatch, in nanoseconds?",
    "What latency does virtual dispatch add per call, per the Kirchner benchmark data?",
    "How many nanoseconds of overhead per call for virtual functions, Kirchner benchmark?",
    "What is the virtual dispatch overhead number from the Kirchner benchmark?",
    "State the nanosecond overhead of virtual function dispatch found by the Kirchner benchmark.",
    "According to the Kirchner benchmark study, how costly is virtual function dispatch per call?",
    "What per-call overhead, in nanoseconds, does the Kirchner benchmark attribute to virtual dispatch?",
    "How many nanoseconds does virtual function dispatch overhead amount to, per Kirchner?",
    "What number does the Kirchner benchmark give for virtual dispatch overhead per call?",
]
assert len(QUERIES) >= 30, f"need >=30 queries, got {len(QUERIES)}"

POSITIONS = [0.0, 0.25, 0.50, 0.75, 1.0]

CHUNK_SIZE = 400
CHUNK_OVERLAP = 50

CONDITIONS = {
    "FULL":     {"multi_granularity": True,  "correction_type": "sin",  "beta": 0.3},
    "ABLATE-A": {"multi_granularity": False, "correction_type": "sin",  "beta": 0.3},
    "ABLATE-B": {"multi_granularity": True,  "correction_type": "none", "beta": 0.0},
    "BASELINE": {"multi_granularity": False, "correction_type": "none", "beta": 0.0},
}
ALPHA = 0.7
ADAPTIVE_GAMMA = True


def insert_needle(text: str, position: float) -> str:
    words = text.split()
    idx = int(len(words) * position)
    return " ".join(words[:idx] + [f"\n\n{NEEDLE_FACT}\n\n"] + words[idx:])


def fixed_size_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """Plain fixed-size word-window chunking — the non-PARA baseline."""
    words = text.split()
    total = len(words)
    chunks = []
    i, cid = 0, 0
    while i < total:
        end = min(i + chunk_size, total)
        content = " ".join(words[i:end])
        position = i / total if total else 0.0
        chunks.append(PARAChunk(content=content, doc_id=f"fixed_{cid}", position=position))
        cid += 1
        i += chunk_size - overlap
    return chunks


def dedup_by_word_overlap(scored, threshold: float = 0.5):
    """Same dedup rule as src/para.py's retrieve_multi_granularity."""
    kept, kept_texts = [], []
    for candidate in scored:
        chunk_words = set(candidate[0].content.lower().split())
        is_dup = False
        for et in kept_texts:
            ew = set(et.lower().split())
            smaller = min(len(chunk_words), len(ew))
            if smaller > 0 and len(chunk_words & ew) / smaller > 0.5:
                is_dup = True
                break
        if not is_dup:
            kept.append(candidate)
            kept_texts.append(candidate[0].content)
    return kept


def dedup_by_prefix(scored, prefix_len: int = 100):
    """Same dedup rule as src/para.py's build_para_context final merge."""
    seen, out = set(), []
    for r in scored:
        key = r[0].content[:prefix_len]
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def build_condition_pools(text: str, condition_cfg: dict):
    """
    Build the chunk pool(s) for one (condition, needle position) pair.
    Chunking is query-independent, so this runs once and is reused for
    all 30 queries via score_chunks' internal embedding cache.
    """
    if condition_cfg["multi_granularity"]:
        base_chunks = semantic_chunk_text(text)
        total_words = len(text.split())
        granularities = multi_granularity_chunks(text, total_words)
        return {"mode": "multi", "base": base_chunks, "granularities": granularities}
    else:
        return {"mode": "fixed", "chunks": fixed_size_chunks(text)}


def score_full_pool(retriever: PARARetriever, query: str, pools: dict,
                     alpha: float, beta: float, correction_type: str, adaptive_gamma: bool):
    """
    Score the ENTIRE candidate pool for one query — no per-level cap, no
    top_k cap (see module docstring: "uncapped full-pool rank").
    Returns the full sorted (chunk, final_score, sem_score, pos_corr) list.
    """
    if pools["mode"] == "fixed":
        return retriever.score_chunks(
            query, pools["chunks"], alpha=alpha, beta=beta,
            correction_type=correction_type, adaptive_gamma=adaptive_gamma,
        )

    # multi-granularity: score sentence/paragraph/section pools, merge+dedup,
    # then merge with the semantic-chunked base pool, dedup again.
    multi_scored = []
    for level_chunks in pools["granularities"].values():
        if not level_chunks:
            continue
        scored = retriever.score_chunks(
            query, level_chunks, alpha=alpha, beta=beta,
            correction_type=correction_type, adaptive_gamma=adaptive_gamma,
        )
        multi_scored.extend(scored)
    multi_scored.sort(key=lambda x: x[1], reverse=True)
    multi_deduped = dedup_by_word_overlap(multi_scored)

    base_scored = retriever.score_chunks(
        query, pools["base"], alpha=alpha, beta=beta,
        correction_type=correction_type, adaptive_gamma=adaptive_gamma,
    )

    all_results = multi_deduped + base_scored
    all_results.sort(key=lambda x: x[1], reverse=True)
    return dedup_by_prefix(all_results)


def needle_rank(ranked_list) -> tuple:
    """Return (rank_1_indexed_or_None, total_candidates)."""
    total = len(ranked_list)
    for i, (chunk, *_rest) in enumerate(ranked_list):
        if NEEDLE_FACT in chunk.content:
            return i + 1, total
    return None, total


def zone_for(position: float) -> str:
    pct = int(round(position * 100))
    return f"{pct}%"


def run():
    print(f"-> Extracting {CORPUS_PATH.name}...")
    pdf_text = extract_text_from_pdf(str(CORPUS_PATH))
    assert not pdf_text.startswith("Error"), pdf_text
    assert "kirchner" not in pdf_text.lower(), "needle fact leaked into corpus"
    total_words = len(pdf_text.split())
    print(f"   {total_words} words\n")

    retriever = PARARetriever()

    rows = []  # raw per-query records
    t0 = time.time()

    for cond_name, cfg in CONDITIONS.items():
        for pos in POSITIONS:
            modified_text = insert_needle(pdf_text, pos)
            t_chunk0 = time.time()
            pools = build_condition_pools(modified_text, cfg)
            chunk_time = time.time() - t_chunk0

            n_pool_desc = (
                f"base={len(pools['base'])} "
                f"sent={len(pools['granularities']['sentence'])} "
                f"para={len(pools['granularities']['paragraph'])} "
                f"sec={len(pools['granularities']['section'])}"
                if pools["mode"] == "multi" else f"fixed={len(pools['chunks'])}"
            )
            print(f"[{cond_name:9s} pos={zone_for(pos):>4s}] chunked in {chunk_time:.1f}s ({n_pool_desc})")

            for q_idx, query in enumerate(QUERIES):
                ranked = score_full_pool(
                    retriever, query, pools,
                    alpha=ALPHA, beta=cfg["beta"],
                    correction_type=cfg["correction_type"],
                    adaptive_gamma=ADAPTIVE_GAMMA,
                )
                rank, total = needle_rank(ranked)
                rows.append({
                    "condition": cond_name,
                    "needle_position_pct": int(round(pos * 100)),
                    "query_idx": q_idx,
                    "query": query,
                    "rank": rank if rank is not None else "",
                    "total_chunks": total,
                    "found": rank is not None,
                    "top1": rank == 1,
                    "top5": rank is not None and rank <= 5,
                })

    elapsed = time.time() - t0
    print(f"\n-> Done in {elapsed:.1f}s. {len(rows)} raw query-level records.\n")
    return rows, total_words


def save_csv(rows, out_path: Path):
    fieldnames = ["condition", "needle_position_pct", "query_idx", "query",
                  "rank", "total_chunks", "found", "top1", "top5"]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"-> Raw CSV saved: {out_path}")


def aggregate(rows):
    """Group by (condition, needle_position_pct) -> summary stats."""
    from collections import defaultdict
    groups = defaultdict(list)
    for r in rows:
        groups[(r["condition"], r["needle_position_pct"])].append(r)

    summary = []
    for (cond, pos), grp in groups.items():
        ranks_found = [r["rank"] for r in grp if r["found"]]
        n = len(grp)
        n_found = len(ranks_found)
        summary.append({
            "condition": cond,
            "position_pct": pos,
            "n_queries": n,
            "n_found": n_found,
            "mean_rank": round(statistics.mean(ranks_found), 2) if ranks_found else None,
            "median_rank": statistics.median(ranks_found) if ranks_found else None,
            "top1_rate": round(sum(1 for r in grp if r["top1"]) / n, 3),
            "top5_rate": round(sum(1 for r in grp if r["top5"]) / n, 3),
            "total_chunks": grp[0]["total_chunks"],
        })
    return summary


def print_summary_table(summary):
    order = ["FULL", "ABLATE-A", "ABLATE-B", "BASELINE"]
    print(f"{'Condition':10s} {'Pos':>5s} {'N':>4s} {'Found':>6s} {'MeanRank':>9s} "
          f"{'MedRank':>8s} {'Top1':>6s} {'Top5':>6s} {'PoolSize':>9s}")
    print("-" * 78)
    for cond in order:
        for row in sorted([s for s in summary if s["condition"] == cond], key=lambda x: x["position_pct"]):
            mr = f"{row['mean_rank']:.1f}" if row["mean_rank"] is not None else "n/a"
            md = f"{row['median_rank']}" if row["median_rank"] is not None else "n/a"
            print(f"{row['condition']:10s} {row['position_pct']:>4d}% {row['n_queries']:>4d} "
                  f"{row['n_found']:>4d}/{row['n_queries']:<2d} {mr:>9s} {md:>8s} "
                  f"{row['top1_rate']:>5.0%} {row['top5_rate']:>5.0%} {row['total_chunks']:>9d}")


if __name__ == "__main__":
    rows, total_words = run()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = PROJECT_ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    csv_path = out_dir / f"retrieval_rank_ablation_{ts}.csv"
    save_csv(rows, csv_path)

    summary = aggregate(rows)
    print("\n=== SUMMARY (condition x needle position) ===")
    print_summary_table(summary)

    import json
    summary_path = out_dir / f"retrieval_rank_ablation_summary_{ts}.json"
    summary_path.write_text(json.dumps({
        "seed": SEED,
        "corpus": str(CORPUS_PATH),
        "corpus_words": total_words,
        "num_queries": len(QUERIES),
        "positions": POSITIONS,
        "conditions": CONDITIONS,
        "alpha": ALPHA,
        "adaptive_gamma": ADAPTIVE_GAMMA,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "summary": summary,
    }, indent=2))
    print(f"\n-> Summary JSON saved: {summary_path}")
