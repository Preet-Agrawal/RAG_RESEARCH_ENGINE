"""
Position-Aware Retrieval Augmentation (PARA)

Novel contribution: Combines semantic embedding retrieval with a sinusoidal
position-bias correction that counteracts the empirical U-shaped attention
drop documented in Liu et al. (2023).

Core formula:
    final_score = alpha * semantic_similarity + beta * gamma * sin(pi * position)

Where:
    - semantic_similarity: cosine similarity between query and chunk embeddings
    - position: chunk's normalized position in document (0.0 to 1.0)
    - sin(pi * position): peaks at 0.5 (document middle), zero at edges
    - alpha, beta, gamma: tunable hyperparameters for ablation
"""

import math
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TextChunk:
    """Represents a chunk of text from the PDF."""
    content: str
    doc_id: str
    position: float


# Lazy-loaded global to avoid re-loading the model on every call
_model_cache = {}


def _get_model(model_name: str):
    """Load and cache the sentence-transformers model."""
    if model_name not in _model_cache:
        from sentence_transformers import SentenceTransformer
        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


class PARARetriever:
    """
    Position-Aware Retrieval Augmentation.

    Scores document chunks using:
        final_score = alpha * semantic_sim + beta * position_correction

    Where position_correction = gamma * sin(pi * position) boosts middle
    chunks that LLMs tend to ignore.
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
        """Cosine similarity between query and each chunk (embeddings are pre-normalized)."""
        return chunk_embeddings @ query_embedding

    @staticmethod
    def compute_position_bias_correction(
        positions: List[float], gamma: float = 0.3
    ) -> np.ndarray:
        """
        Sinusoidal position-bias correction.

        Returns a boost that is highest at position 0.5 (document middle)
        and zero at positions 0.0 and 1.0 (document edges where LLM
        attention is already high).

        This mathematically counteracts the U-shaped attention pattern:
            correction_i = gamma * sin(pi * position_i)
        """
        return np.array([gamma * math.sin(math.pi * p) for p in positions])

    def score_chunks(
        self,
        query: str,
        chunks: List[TextChunk],
        alpha: float = 0.7,
        beta: float = 0.3,
        gamma: float = 0.3,
    ) -> List[Tuple[TextChunk, float, float, float]]:
        """
        Score all chunks using the PARA formula.

        Returns: List of (chunk, final_score, semantic_score, position_correction)
                 sorted by final_score descending.
        """
        if not chunks:
            return []

        # Compute embeddings
        query_emb = self.embed_query(query)
        chunk_texts = [c.content for c in chunks]
        chunk_embs = self.embed_texts(chunk_texts)

        # Semantic similarity scores
        semantic_scores = self.compute_semantic_scores(query_emb, chunk_embs)

        # Position bias correction
        positions = [c.position for c in chunks]
        pos_corrections = self.compute_position_bias_correction(positions, gamma)

        # PARA combined score
        final_scores = alpha * semantic_scores + beta * pos_corrections

        # Bundle results
        results = []
        for i, chunk in enumerate(chunks):
            results.append((
                chunk,
                float(final_scores[i]),
                float(semantic_scores[i]),
                float(pos_corrections[i]),
            ))

        # Sort by final score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def retrieve_top_k(
        self,
        query: str,
        chunks: List[TextChunk],
        k: int = 10,
        alpha: float = 0.7,
        beta: float = 0.3,
        gamma: float = 0.3,
    ) -> List[Tuple[TextChunk, float, float, float]]:
        """Return top-k chunks by PARA score."""
        scored = self.score_chunks(query, chunks, alpha, beta, gamma)
        return scored[:k]

    def build_para_context(
        self,
        query: str,
        chunks: List[TextChunk],
        top_k: int = 10,
        alpha: float = 0.7,
        beta: float = 0.3,
        gamma: float = 0.3,
    ) -> Tuple[str, float]:
        """
        Build a context string from the top-k PARA-scored chunks.

        Returns:
            (context_string, avg_semantic_similarity)

        The avg_semantic_similarity serves as a confidence proxy —
        much better than the heuristic 0.85 used by other strategies.
        """
        scored = self.retrieve_top_k(query, chunks, top_k, alpha, beta, gamma)

        if not scored:
            return "", 0.0

        avg_semantic = sum(s[2] for s in scored) / len(scored)

        parts = []
        # Query before documents (query-aware contextualization)
        parts.append(f"QUESTION: {query}")
        parts.append(f"\nRetrieved {len(scored)} most relevant sections using semantic search with position-aware scoring.\n")
        parts.append("=" * 60)

        for rank, (chunk, final_score, sem_score, pos_corr) in enumerate(scored):
            position_pct = int(chunk.position * 100)
            parts.append(
                f"\n--- SECTION {rank+1}/{len(scored)} "
                f"(Relevance: {final_score:.3f} | Position: {position_pct}%) ---"
            )
            parts.append(chunk.content)

        parts.append("\n" + "=" * 60)
        # Query after documents
        parts.append(f"\nBased on ALL the retrieved sections above, answer: {query}")
        parts.append("\nProvide a detailed answer using information from any section:")

        return "\n".join(parts), avg_semantic
