"""
Unit tests for the pure chunking/restructuring logic in process_pdf.py.

MiddleRecoveryProcessor normally wraps an LLM client, but chunk_text and
_place_at_edges never touch self.llm_client, so we can instantiate it with
llm_client=None and test the pure logic directly - no API calls involved.
"""
import pytest

from process_pdf import MiddleRecoveryProcessor, TextChunk


processor = MiddleRecoveryProcessor(llm_client=None)


# ── chunk_text ────────────────────────────────────────────────────────────


def test_chunk_text_overlaps_and_tracks_position():
    words = [f"word{i}" for i in range(25)]
    text = " ".join(words)

    chunks = processor.chunk_text(text, chunk_size=10, overlap=2)

    # 25 words, stepping by (10 - 2) = 8: starts at 0, 8, 16, 24 -> 4 chunks.
    assert len(chunks) == 4

    # First chunk starts at the beginning of the document.
    assert chunks[0].position == 0.0
    # Positions strictly increase with each subsequent chunk.
    positions = [c.position for c in chunks]
    assert positions == sorted(positions)
    assert len(set(positions)) == len(positions)

    # Consecutive chunks actually overlap by the requested word count.
    first_words = chunks[0].content.split()
    second_words = chunks[1].content.split()
    assert first_words[-2:] == second_words[:2]


def test_chunk_text_handles_empty_text():
    assert processor.chunk_text("", chunk_size=10, overlap=2) == []


# ── _place_at_edges (the "lost in the middle" mitigation) ───────────────────


def test_place_at_edges_pushes_highest_relevance_to_the_edges():
    # Pre-sorted descending by score, as apply_relevance_restructuring does.
    scored_chunks = [
        (TextChunk(content=f"chunk{i}", doc_id=f"c{i}", position=0.0), score)
        for i, score in enumerate([5, 4, 3, 2, 1])
    ]

    result = MiddleRecoveryProcessor._place_at_edges(scored_chunks)
    result_scores = [score for _, score in result]

    # Alternating left/right fill: highest two scores land at the two edges,
    # the lowest score lands dead center - the opposite of where an LLM's
    # attention is weakest.
    assert result_scores == [5, 3, 1, 2, 4]
    assert result_scores[0] == 5
    assert result_scores[-1] == 4
    assert result_scores[len(result_scores) // 2] == min(result_scores)


def test_place_at_edges_preserves_all_items():
    scored_chunks = [
        (TextChunk(content=f"chunk{i}", doc_id=f"c{i}", position=0.0), i)
        for i in range(6)
    ]

    result = MiddleRecoveryProcessor._place_at_edges(scored_chunks)

    assert len(result) == len(scored_chunks)
    assert {score for _, score in result} == {score for _, score in scored_chunks}
