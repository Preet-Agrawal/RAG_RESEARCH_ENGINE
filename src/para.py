"""
Position-Aware Retrieval Augmentation (PARA) — Enhanced

Novel contributions:
  1. Semantic embeddings + sinusoidal position-bias correction
  2. Adaptive gamma — correction scales with document length
  3. Multi-granularity retrieval — sentence, paragraph, and section levels
  4. Cross-encoder reranking — rerank top-k with higher accuracy model
  5. Semantic chunking — split at topic boundaries, not fixed word count

Core formula:
    final_score = alpha * semantic_similarity + beta * gamma_adaptive * sin(pi * position)

Where gamma_adaptive = base_gamma * log(num_chunks) / log(10)
"""

import math
import re
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class TextChunk:
    """Represents a chunk of text from the PDF."""
    content: str
    doc_id: str
    position: float
    granularity: str = "paragraph"  # "sentence", "paragraph", or "section"


# ── Model Cache ──────────────────────────────────────────────────────────────

_model_cache = {}


def _get_model(model_name: str):
    """Load and cache the sentence-transformers model."""
    if model_name not in _model_cache:
        from sentence_transformers import SentenceTransformer
        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


def _get_cross_encoder(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
    """Load and cache a cross-encoder model for reranking."""
    key = f"cross_{model_name}"
    if key not in _model_cache:
        from sentence_transformers import CrossEncoder
        _model_cache[key] = CrossEncoder(model_name)
    return _model_cache[key]


# ── Semantic Chunking ────────────────────────────────────────────────────────


def semantic_chunk_text(
    text: str,
    model_name: str = "all-MiniLM-L6-v2",
    max_chunk_words: int = 500,
    min_chunk_words: int = 80,
    similarity_threshold: float = 0.5,
) -> List[TextChunk]:
    """
    Split text at topic boundaries using embedding similarity.

    Instead of blindly splitting every N words, this detects where the
    topic changes by comparing consecutive paragraph embeddings. When
    similarity drops below the threshold, a new chunk starts.

    This preserves semantic coherence within each chunk.
    """
    # Split into paragraphs (or sentences for short docs)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n|\n(?=[A-Z])', text) if p.strip()]

    # If too few paragraphs, fall back to sentence splitting
    if len(paragraphs) < 5:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        paragraphs = [s.strip() for s in sentences if s.strip() and len(s.split()) > 3]

    if not paragraphs:
        return [TextChunk(content=text, doc_id="chunk_0", position=0.0)]

    # Embed all paragraphs
    model = _get_model(model_name)
    embeddings = model.encode(paragraphs, convert_to_numpy=True, normalize_embeddings=True)

    # Group paragraphs into chunks by similarity
    chunks = []
    current_group = [paragraphs[0]]
    current_word_count = len(paragraphs[0].split())
    total_words = sum(len(p.split()) for p in paragraphs)
    word_offset = 0

    for i in range(1, len(paragraphs)):
        # Cosine similarity between consecutive paragraphs
        sim = float(embeddings[i] @ embeddings[i - 1])

        para_words = len(paragraphs[i].split())

        # Start new chunk if: topic changed AND current chunk is big enough
        # OR current chunk is too large
        should_split = (
            (sim < similarity_threshold and current_word_count >= min_chunk_words)
            or current_word_count + para_words > max_chunk_words
        )

        if should_split and current_group:
            chunk_text = "\n\n".join(current_group)
            position = word_offset / total_words if total_words > 0 else 0
            chunks.append(TextChunk(
                content=chunk_text,
                doc_id=f"chunk_{len(chunks)}",
                position=position,
                granularity="paragraph",
            ))
            word_offset += current_word_count
            current_group = [paragraphs[i]]
            current_word_count = para_words
        else:
            current_group.append(paragraphs[i])
            current_word_count += para_words

    # Last chunk
    if current_group:
        chunk_text = "\n\n".join(current_group)
        position = word_offset / total_words if total_words > 0 else 0
        chunks.append(TextChunk(
            content=chunk_text,
            doc_id=f"chunk_{len(chunks)}",
            position=position,
            granularity="paragraph",
        ))

    return chunks


# ── Multi-Granularity Chunking ───────────────────────────────────────────────


def multi_granularity_chunks(text: str, total_words: int = 0) -> dict:
    """
    Create chunks at 3 granularity levels simultaneously:
      - sentence: individual sentences (~20-40 words)
      - paragraph: natural paragraphs (~100-300 words)
      - section: large sections (~500-800 words)

    Returns dict with keys: "sentence", "paragraph", "section"
    """
    if total_words == 0:
        total_words = len(text.split())

    result = {"sentence": [], "paragraph": [], "section": []}

    # Sentence-level
    sentences = re.split(r'(?<=[.!?])\s+', text)
    word_offset = 0
    for i, sent in enumerate(sentences):
        sent = sent.strip()
        if len(sent.split()) < 5:
            continue
        position = word_offset / total_words if total_words > 0 else 0
        result["sentence"].append(TextChunk(
            content=sent, doc_id=f"sent_{i}", position=position, granularity="sentence"
        ))
        word_offset += len(sent.split())

    # Paragraph-level
    paragraphs = [p.strip() for p in text.split('\n') if p.strip() and len(p.split()) > 10]
    word_offset = 0
    for i, para in enumerate(paragraphs):
        position = word_offset / total_words if total_words > 0 else 0
        result["paragraph"].append(TextChunk(
            content=para, doc_id=f"para_{i}", position=position, granularity="paragraph"
        ))
        word_offset += len(para.split())

    # Section-level (group paragraphs into ~500-word sections)
    words = text.split()
    section_size = 500
    overlap = 50
    idx = 0
    sec_id = 0
    while idx < len(words):
        end = min(idx + section_size, len(words))
        section_text = " ".join(words[idx:end])
        position = idx / total_words if total_words > 0 else 0
        result["section"].append(TextChunk(
            content=section_text, doc_id=f"sec_{sec_id}", position=position, granularity="section"
        ))
        sec_id += 1
        idx += section_size - overlap

    return result


# ── PARA Retriever ───────────────────────────────────────────────────────────


class PARARetriever:
    """
    Position-Aware Retrieval Augmentation (Enhanced).

    Features:
        1. Semantic similarity scoring (bi-encoder)
        2. Sinusoidal position-bias correction (adaptive gamma)
        3. Multi-granularity retrieval (sentence + paragraph + section)
        4. Cross-encoder reranking for top results
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = _get_model(model_name)

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Encode a list of texts into embeddings."""
        return self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    def embed_query(self, query: str) -> np.ndarray:
        """Encode a single query into an embedding."""
        return self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]

    def compute_semantic_scores(
        self, query_embedding: np.ndarray, chunk_embeddings: np.ndarray
    ) -> np.ndarray:
        """Cosine similarity between query and each chunk."""
        return chunk_embeddings @ query_embedding

    @staticmethod
    def compute_adaptive_gamma(num_chunks: int, base_gamma: float = 0.3) -> float:
        """
        Adaptive gamma — scales position correction with document length.

        Longer documents have worse middle-attention drops, so they need
        stronger position correction.

        Formula: gamma = base_gamma * log(num_chunks) / log(10)
          - 5 chunks  → gamma = 0.21 (mild correction)
          - 10 chunks → gamma = 0.30 (default)
          - 30 chunks → gamma = 0.44 (stronger)
          - 100 chunks → gamma = 0.60 (heavy correction)
        """
        if num_chunks <= 1:
            return 0.0
        return base_gamma * math.log(max(num_chunks, 2)) / math.log(10)

    @staticmethod
    def compute_position_bias_correction(
        positions: List[float], gamma: float = 0.3
    ) -> np.ndarray:
        """
        Sinusoidal position-bias correction.
        correction_i = gamma * sin(pi * position_i)
        """
        return np.array([gamma * math.sin(math.pi * p) for p in positions])

    def score_chunks(
        self,
        query: str,
        chunks: List[TextChunk],
        alpha: float = 0.7,
        beta: float = 0.3,
        gamma: float = None,  # None = use adaptive gamma
    ) -> List[Tuple[TextChunk, float, float, float]]:
        """
        Score all chunks using the PARA formula with adaptive gamma.

        Returns: List of (chunk, final_score, semantic_score, position_correction)
                 sorted by final_score descending.
        """
        if not chunks:
            return []

        # Adaptive gamma based on document length
        if gamma is None:
            gamma = self.compute_adaptive_gamma(len(chunks))

        # Compute embeddings
        query_emb = self.embed_query(query)
        chunk_texts = [c.content for c in chunks]
        chunk_embs = self.embed_texts(chunk_texts)

        # Semantic similarity
        semantic_scores = self.compute_semantic_scores(query_emb, chunk_embs)

        # Position bias correction
        positions = [c.position for c in chunks]
        pos_corrections = self.compute_position_bias_correction(positions, gamma)

        # PARA combined score
        final_scores = alpha * semantic_scores + beta * pos_corrections

        results = []
        for i, chunk in enumerate(chunks):
            results.append((
                chunk,
                float(final_scores[i]),
                float(semantic_scores[i]),
                float(pos_corrections[i]),
            ))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def cross_encoder_rerank(
        self,
        query: str,
        scored_chunks: List[Tuple[TextChunk, float, float, float]],
        top_n: int = 5,
    ) -> List[Tuple[TextChunk, float, float, float]]:
        """
        Rerank the top candidates using a cross-encoder for higher accuracy.

        Bi-encoders are fast but encode query and chunk independently.
        Cross-encoders see both together, giving much more accurate relevance.

        Only reranks the top candidates (default 5) to keep latency low.
        """
        if len(scored_chunks) <= 1:
            return scored_chunks

        candidates = scored_chunks[:top_n]
        rest = scored_chunks[top_n:]

        try:
            cross_encoder = _get_cross_encoder()
            pairs = [(query, chunk.content) for chunk, _, _, _ in candidates]
            ce_scores = cross_encoder.predict(pairs)

            # Normalize cross-encoder scores to [0, 1]
            ce_min, ce_max = float(min(ce_scores)), float(max(ce_scores))
            if ce_max > ce_min:
                ce_normalized = [(s - ce_min) / (ce_max - ce_min) for s in ce_scores]
            else:
                ce_normalized = [0.5] * len(ce_scores)

            # Blend: 60% cross-encoder + 40% original PARA score
            reranked = []
            for i, (chunk, para_score, sem_score, pos_corr) in enumerate(candidates):
                blended = 0.6 * ce_normalized[i] + 0.4 * para_score
                reranked.append((chunk, blended, sem_score, pos_corr))

            reranked.sort(key=lambda x: x[1], reverse=True)
            return reranked + rest

        except Exception:
            # If cross-encoder fails, return original ranking
            return scored_chunks

    def retrieve_top_k(
        self,
        query: str,
        chunks: List[TextChunk],
        k: int = 10,
        alpha: float = 0.7,
        beta: float = 0.3,
        gamma: float = None,
        use_cross_encoder: bool = True,
    ) -> List[Tuple[TextChunk, float, float, float]]:
        """Return top-k chunks by PARA score, optionally reranked by cross-encoder."""
        scored = self.score_chunks(query, chunks, alpha, beta, gamma)

        if use_cross_encoder and len(scored) > 3:
            scored = self.cross_encoder_rerank(query, scored, top_n=min(k, len(scored)))

        return scored[:k]

    def retrieve_multi_granularity(
        self,
        query: str,
        text: str,
        k_per_level: int = 5,
        alpha: float = 0.7,
        beta: float = 0.3,
    ) -> List[Tuple[TextChunk, float, float, float]]:
        """
        Retrieve from sentence, paragraph, and section levels simultaneously.

        Merges the best from each granularity and deduplicates by content overlap.
        """
        total_words = len(text.split())
        granularities = multi_granularity_chunks(text, total_words)

        all_candidates = []
        for level_name, level_chunks in granularities.items():
            if not level_chunks:
                continue
            scored = self.score_chunks(query, level_chunks, alpha, beta)
            all_candidates.extend(scored[:k_per_level])

        # Deduplicate: if two chunks overlap >50% in words, keep the higher-scored one
        all_candidates.sort(key=lambda x: x[1], reverse=True)
        kept = []
        kept_texts = []
        for candidate in all_candidates:
            chunk_words = set(candidate[0].content.lower().split())
            is_duplicate = False
            for existing_text in kept_texts:
                existing_words = set(existing_text.lower().split())
                overlap = len(chunk_words & existing_words)
                smaller = min(len(chunk_words), len(existing_words))
                if smaller > 0 and overlap / smaller > 0.5:
                    is_duplicate = True
                    break
            if not is_duplicate:
                kept.append(candidate)
                kept_texts.append(candidate[0].content)

        return kept

    def build_para_context(
        self,
        query: str,
        chunks: List[TextChunk],
        top_k: int = 10,
        alpha: float = 0.7,
        beta: float = 0.3,
        gamma: float = None,
        use_cross_encoder: bool = True,
        full_text: str = None,
    ) -> Tuple[str, float]:
        """
        Build a context string from the top-k PARA-scored chunks.

        If full_text is provided, uses multi-granularity retrieval.

        Returns:
            (context_string, avg_semantic_similarity)
        """
        if full_text and len(full_text.split()) > 200:
            # Multi-granularity retrieval
            multi_results = self.retrieve_multi_granularity(
                query, full_text, k_per_level=max(3, top_k // 3), alpha=alpha, beta=beta
            )
            # Also get standard PARA results and merge
            standard_results = self.retrieve_top_k(
                query, chunks, top_k, alpha, beta, gamma, use_cross_encoder
            )
            # Merge and deduplicate
            all_results = multi_results + standard_results
            all_results.sort(key=lambda x: x[1], reverse=True)
            # Deduplicate
            seen = set()
            scored = []
            for r in all_results:
                key = r[0].content[:100]
                if key not in seen:
                    seen.add(key)
                    scored.append(r)
                if len(scored) >= top_k:
                    break
        else:
            scored = self.retrieve_top_k(
                query, chunks, top_k, alpha, beta, gamma, use_cross_encoder
            )

        if not scored:
            return "", 0.0

        avg_semantic = sum(s[2] for s in scored) / len(scored)

        parts = []
        parts.append(f"QUESTION: {query}")
        parts.append(f"\nRetrieved {len(scored)} most relevant sections using semantic search with position-aware scoring.\n")
        parts.append("=" * 60)

        for rank, (chunk, final_score, sem_score, pos_corr) in enumerate(scored):
            position_pct = int(chunk.position * 100)
            granularity_tag = f" [{chunk.granularity}]" if chunk.granularity != "paragraph" else ""
            parts.append(
                f"\n--- SECTION {rank+1}/{len(scored)} "
                f"(Relevance: {final_score:.3f} | Position: {position_pct}%{granularity_tag}) ---"
            )
            parts.append(chunk.content)

        parts.append("\n" + "=" * 60)
        parts.append(f"\nBased on ALL the retrieved sections above, answer: {query}")
        parts.append("\nProvide a detailed answer using information from any section:")

        return "\n".join(parts), avg_semantic
