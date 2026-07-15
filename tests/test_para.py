"""
Unit tests for the pure math/logic in src/para.py — the PARA scoring formula.

None of these touch sentence-transformers models, so they run fast and
don't need network access or a GPU.
"""
import math

import numpy as np
import pytest

import src.para as para_module
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


# ── retrieve_multi_granularity correction_type propagation (regression) ─────
#
# Bug: retrieve_multi_granularity() never passed correction_type/gamma/
# adaptive_gamma through to its internal score_chunks() call, so it silently
# used score_chunks()'s own default ("sin") regardless of what the caller
# (build_para_context / apply_para) requested. correction_type="none" looked
# like it disabled position correction but didn't, when reached via
# use_multi_granularity=True (the production default).


def test_retrieve_multi_granularity_propagates_correction_type_none(monkeypatch):
    # Stub model loading and embeddings so this never touches
    # sentence-transformers (not installed in this test environment, and not
    # needed): _get_model is patched so PARARetriever() can be constructed
    # without a real model, and embed_query/embed_texts return a constant,
    # parallel vector so every chunk gets cosine similarity 1.0 to the query
    # regardless of content or position. That isolates position correction as
    # the *only* possible source of score variation.
    monkeypatch.setattr(para_module, "_get_model", lambda model_name: None)
    monkeypatch.setattr(
        PARARetriever, "embed_query",
        lambda self, query: np.array([1.0, 0.0]),
    )
    monkeypatch.setattr(
        PARARetriever, "embed_texts",
        lambda self, texts: np.tile(np.array([1.0, 0.0]), (len(texts), 1)),
    )

    text = (
        "Alpha sentence starts the document right at the very beginning part.\n"
        "\n"
        "Beta sentence sits somewhere in the middle of the whole document body.\n"
        "\n"
        "Gamma sentence continues further along in the middle region as well.\n"
        "\n"
        "Delta sentence closes out the document near its very final ending part.\n"
    )

    retriever = PARARetriever()
    results = retriever.retrieve_multi_granularity(
        "irrelevant query", text, k_per_level=5, alpha=0.7, beta=0.3,
        correction_type="none",
    )

    assert results, "expected at least one candidate"

    # With correction_type="none" genuinely propagated, position correction
    # must be exactly zero for every candidate, regardless of its position
    # (a chunk sitting mid-document would get a large nonzero "sin" boost if
    # the bug were still present).
    pos_corrections = [pos_corr for (_chunk, _final, _sem, pos_corr) in results]
    assert pos_corrections == pytest.approx([0.0] * len(pos_corrections), abs=1e-9)

    # Semantic similarity is pinned at 1.0 for every chunk, so with no
    # position contribution every final score must equal alpha (0.7) exactly
    # -- no positional spread between chunks.
    final_scores = [final for (_chunk, final, _sem, _pos) in results]
    assert final_scores == pytest.approx([0.7] * len(final_scores), abs=1e-9)
