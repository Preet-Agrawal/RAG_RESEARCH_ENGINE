"""
Unit tests for the pure math/logic in src/para.py — the PARA scoring formula.

None of these touch sentence-transformers models, so they run fast and
don't need network access or a GPU.
"""
import math

import numpy as np
import pytest

from src.para import PARARetriever, multi_granularity_chunks


# ── compute_semantic_scores (cosine similarity) ─────────────────────────────


def test_compute_semantic_scores_is_cosine_similarity():
    # Vectors are already unit-normalized, as embed_query/embed_texts produce.
    query = np.array([1.0, 0.0])
    chunks = np.array([
        [1.0, 0.0],   # parallel -> similarity 1
        [0.0, 1.0],   # orthogonal -> similarity 0
        [-1.0, 0.0],  # opposite -> similarity -1
    ])

    scores = PARARetriever.compute_semantic_scores(query, chunks)

    assert scores == pytest.approx([1.0, 0.0, -1.0])


# ── compute_adaptive_gamma ───────────────────────────────────────────────────


def test_compute_adaptive_gamma_matches_documented_values_and_is_monotonic():
    # Values asserted in the function's own docstring.
    assert PARARetriever.compute_adaptive_gamma(1) == 0.0
    assert PARARetriever.compute_adaptive_gamma(5) == pytest.approx(0.21, abs=0.01)
    assert PARARetriever.compute_adaptive_gamma(10) == pytest.approx(0.30, abs=0.01)
    assert PARARetriever.compute_adaptive_gamma(100) == pytest.approx(0.60, abs=0.01)

    # More chunks -> stronger correction (monotonic increase).
    gammas = [PARARetriever.compute_adaptive_gamma(n) for n in (2, 5, 10, 30, 100)]
    assert gammas == sorted(gammas)


# ── compute_position_bias_correction ─────────────────────────────────────────


def test_position_bias_correction_sin_peaks_at_center_and_vanishes_at_edges():
    positions = [0.0, 0.5, 1.0]
    correction = PARARetriever.compute_position_bias_correction(
        positions, gamma=0.3, correction_type="sin"
    )

    assert correction[0] == pytest.approx(0.0, abs=1e-9)
    assert correction[1] == pytest.approx(0.3, abs=1e-9)  # sin(pi/2) == 1
    assert correction[2] == pytest.approx(0.0, abs=1e-9)


def test_position_bias_correction_none_and_step_variants():
    positions = [0.0, 0.25, 0.5, 0.75, 1.0]

    none_correction = PARARetriever.compute_position_bias_correction(
        positions, gamma=0.3, correction_type="none"
    )
    assert list(none_correction) == [0.0, 0.0, 0.0, 0.0, 0.0]

    step_correction = PARARetriever.compute_position_bias_correction(
        positions, gamma=0.3, correction_type="step"
    )
    # Inclusive boundaries per the docstring: gamma for 0.25 <= p <= 0.75.
    assert list(step_correction) == [0.0, 0.3, 0.3, 0.3, 0.0]


# ── multi_granularity_chunks ─────────────────────────────────────────────────


def test_multi_granularity_chunks_splits_into_sane_sentence_and_paragraph_counts():
    text = (
        "Alpha is the first concept. Beta follows alpha closely. Gamma comes third.\n"
        "\n"
        "Delta starts a new paragraph with its own long sentence to describe things.\n"
        "Epsilon continues that paragraph with more detail about the topic at hand.\n"
    )

    result = multi_granularity_chunks(text)

    assert set(result.keys()) == {"sentence", "paragraph", "section"}
    assert len(result["sentence"]) >= 3
    assert len(result["paragraph"]) >= 1

    # Positions should be non-decreasing within each granularity level.
    for level_chunks in result.values():
        positions = [c.position for c in level_chunks]
        assert positions == sorted(positions)
        assert all(0.0 <= p <= 1.0 for p in positions)
