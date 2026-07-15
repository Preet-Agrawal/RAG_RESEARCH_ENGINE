#!/usr/bin/env python3
"""
Diagnostic (no LLM calls) to find a real configuration where:
  - the needle IS recall-eligible (has a competitive semantic score), but
  - ranks OUTSIDE top_k by semantic score alone (correction_type="none"), and
  - ranks INSIDE top_k once PARA's position correction is applied (correction_type="sin").

This is the specific case PARA_EMPIRICAL_FINDINGS.md §7 flagged as never having
been isolated: recall-eligible but low-ranked, where reordering (not recall)
is what decides the outcome. Everything here is a real embedding computation
against PARARetriever — no fabricated numbers, no LLM cost.
"""
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from process_pdf import extract_text_from_pdf
from src.para import PARARetriever, multi_granularity_chunks, TextChunk

PDF_PATH = PROJECT_ROOT / "data" / "uploads" / "Cpp_repaired_trimmed_210pages.pdf"

QUESTION = ("According to the Kirchner benchmark, how many nanoseconds "
            "of overhead does virtual function dispatch add per call?")

NEEDLE = ("The Kirchner benchmark found that dispatching a call through a "
          "virtual table costs an extra 7 nanoseconds each time it happens.")
NEEDLE_POSITION = 0.5

# Deliberately templated to closely mirror the query's own phrasing
# ("According to the X benchmark, virtual [function] dispatch ... nanoseconds
# ... per call") — measured standalone at 0.78-0.88 cosine similarity against
# the query, i.e. higher than the needle's own 0.7581. None of them state the
# real answer (7ns); they all say "ten nanoseconds" or a vague equivalent.
DISTRACTORS = [
    "According to the Alexandrescu benchmark, virtual dispatch overhead is typically under ten nanoseconds on x86 hardware.",
    "According to the Torvalds benchmark, virtual function dispatch overhead is typically around ten nanoseconds per call.",
    "According to the Knuth benchmark, virtual function dispatch overhead measures about ten nanoseconds per call on average.",
    "According to the Booch benchmark, virtual function dispatch adds approximately ten nanoseconds of overhead per call.",
    "According to the Liskov benchmark, virtual function dispatch overhead is roughly ten nanoseconds per call on typical hardware.",
    "According to the Dijkstra benchmark, the overhead of virtual function dispatch is about ten nanoseconds per call.",
    "According to the Hoare benchmark, virtual function dispatch adds around ten nanoseconds of overhead for every call.",
    "According to the Wirth benchmark, virtual function dispatch overhead comes to roughly ten nanoseconds per invocation.",
    "According to the Backus benchmark, virtual function dispatch adds about ten nanoseconds of overhead per function call.",
    "According to the Naur benchmark, the overhead added by virtual function dispatch is approximately ten nanoseconds per call.",
    "According to the Iverson benchmark, virtual function dispatch overhead per call is close to ten nanoseconds.",
    "According to the Ritchie benchmark, virtual function dispatch adds close to ten nanoseconds of overhead on each call.",
]
# Two edge positions, each getting a CLUSTER of 6 distractor sentences
# inserted as one contiguous paragraph (not scattered individually). A lone
# isolated distractor sentence gets diluted when top-level semantic chunking
# (~500-word chunks) merges it with surrounding real book text; a cluster of
# 6 mutually-similar sentences forms its own coherent topic-chunk that
# survives that dilution — same reason the needle itself resists dilution
# less than a single stray sentence would.
DISTRACTOR_CLUSTER_POSITIONS = [0.02, 0.98]


def _word_boundaries(text: str):
    """Character offset immediately after each whitespace-delimited word."""
    return [m.end() for m in re.finditer(r"\S+", text)]


def insert_at(text: str, insertion: str, position: float) -> str:
    """Insert at the character offset of the Nth word, WITHOUT touching any
    other whitespace/newlines in the rest of the document. Earlier versions
    of this script did text.split() + " ".join(), which silently destroyed
    every real newline in the source PDF before semantic_chunk_text() ever
    saw it — collapsing a 43k-word document's paragraph structure down to a
    handful of oversized chunks. That was a bug in this test harness, not in
    src/para.py: verified by running semantic_chunk_text() on the
    unmodified PDF (326 sensible ~130-word chunks) vs. the word-split/rejoin
    version (7-16 chunks). This version preserves the original text exactly
    except at the insertion point.
    """
    boundaries = _word_boundaries(text)
    idx = int(len(boundaries) * position)
    offset = boundaries[idx] if idx < len(boundaries) else len(text)
    # Force a clean sentence boundary at the insertion point only.
    return text[:offset] + f" .\n\n{insertion}\n\n" + text[offset:]


def build_document(base_text: str) -> str:
    half = len(DISTRACTORS) // 2
    clusters = [
        (DISTRACTOR_CLUSTER_POSITIONS[0], " ".join(DISTRACTORS[:half])),
        (DISTRACTOR_CLUSTER_POSITIONS[1], " ".join(DISTRACTORS[half:])),
    ]
    insertions = [(NEEDLE_POSITION, NEEDLE)] + clusters
    # Insert from the end backwards so earlier word-boundary offsets stay valid.
    insertions.sort(key=lambda x: x[0], reverse=True)

    text = base_text
    for pos, insertion in insertions:
        text = insert_at(text, insertion, pos)

    return text


def find_rank(scored, marker: str):
    for i, s in enumerate(scored):
        if marker in s[0].content:
            return i + 1, s
    return None, None


def main():
    print(f"-> Loading {PDF_PATH.name}...")
    base_text = extract_text_from_pdf(str(PDF_PATH))
    print(f"   base doc: {len(base_text.split())} words")

    for marker in ["Kirchner benchmark found", "kirchner"]:
        assert marker.lower() not in base_text.lower(), f"'{marker}' already present natively!"

    doc = build_document(base_text)
    total_words = len(doc.split())
    print(f"-> Built doc with needle + {len(DISTRACTORS)} distractors: {total_words} words\n")

    retriever = PARARetriever()
    granularities = multi_granularity_chunks(doc, total_words)
    sentence_pool = granularities["sentence"]
    print(f"-> Sentence-level candidate pool: {len(sentence_pool)} chunks\n")

    needle_key = "extra 7 nanoseconds"

    for label, correction_type, adaptive in [
        ("Semantic only (correction_type=none)", "none", False),
        ("Full PARA (correction_type=sin, adaptive_gamma=True)", "sin", True),
    ]:
        scored = retriever.score_chunks(QUESTION, sentence_pool, alpha=0.7, beta=0.3,
                                         correction_type=correction_type, adaptive_gamma=adaptive)
        rank, entry = find_rank(scored, needle_key)
        print(f"=== {label} ===")
        if entry:
            chunk, final_score, sem_score, pos_corr = entry
            print(f"  needle rank: {rank} / {len(scored)}")
            print(f"  semantic_sim={sem_score:.4f}  position_correction={pos_corr:.4f}  final_score={final_score:.4f}")
            print(f"  in top_10: {rank <= 10}")
        else:
            print("  needle NOT FOUND in pool (marker mismatch?)")

        print(f"  top 10:")
        for i, (chunk, fs, ss, pc) in enumerate(scored[:10]):
            tag = " <== NEEDLE" if needle_key in chunk.content else ""
            preview = chunk.content.strip().replace("\n", " ")[:70]
            print(f"    {i+1:2d}. final={fs:.4f} sem={ss:.4f} pos_corr={pc:.4f} p={chunk.position:.3f}  {preview!r}{tag}")
        print()


if __name__ == "__main__":
    main()
