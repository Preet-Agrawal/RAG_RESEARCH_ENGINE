"""
Strategy 1: Intelligent Context Restructuring

Dynamically reorganizes documents so relevant information isn't in the dead zone.
"""
from typing import List, Dict, Any
import numpy as np


class ContextRestructuringStrategy:
    """
    Reorganize documents to avoid placing important content in the dead zone.

    Strategy:
    1. Estimate relevance of each document to the query
    2. Place high-relevance documents at the edges (start/end)
    3. Place low-relevance documents in the middle
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def restructure(self, documents: List, query: str, method: str = "relevance") -> List:
        """
        Restructure documents based on strategy.

        Args:
            documents: List of Document objects
            query: The question to be answered
            method: Restructuring method ('relevance', 'alternating', 'reverse')

        Returns:
            Reordered list of documents
        """
        if method == "relevance":
            return self._restructure_by_relevance(documents, query)
        elif method == "alternating":
            return self._restructure_alternating(documents, query)
        elif method == "reverse":
            return self._restructure_reverse(documents)
        elif method == "random":
            return self._restructure_random(documents)
        else:
            return documents  # No restructuring (baseline)

    def _restructure_by_relevance(self, documents: List, query: str) -> List:
        """
        Place relevant documents at edges, irrelevant in middle.

        High-relevance docs: positions 0, -1, 1, -2, 2, -3, ...
        Low-relevance docs: middle positions
        """
        # Estimate relevance scores
        relevance_scores = self._estimate_relevance(documents, query)

        # Sort documents by relevance (descending)
        doc_relevance = list(zip(documents, relevance_scores))
        doc_relevance.sort(key=lambda x: x[1], reverse=True)

        # Restructure: alternating high-relevance docs at start and end
        restructured = [None] * len(documents)
        left_idx = 0
        right_idx = len(documents) - 1

        for i, (doc, score) in enumerate(doc_relevance):
            if i % 2 == 0:
                # Place at start
                restructured[left_idx] = doc
                left_idx += 1
            else:
                # Place at end
                restructured[right_idx] = doc
                right_idx -= 1

        return restructured

    def _restructure_alternating(self, documents: List, query: str) -> List:
        """
        Alternate between high and low relevance documents.
        """
        relevance_scores = self._estimate_relevance(documents, query)
        doc_relevance = list(zip(documents, relevance_scores))
        doc_relevance.sort(key=lambda x: x[1], reverse=True)

        # Split into high and low relevance
        mid = len(doc_relevance) // 2
        high_rel = [doc for doc, _ in doc_relevance[:mid]]
        low_rel = [doc for doc, _ in doc_relevance[mid:]]

        # Alternate
        restructured = []
        for i in range(max(len(high_rel), len(low_rel))):
            if i < len(high_rel):
                restructured.append(high_rel[i])
            if i < len(low_rel):
                restructured.append(low_rel[i])

        return restructured

    def _restructure_reverse(self, documents: List) -> List:
        """Simply reverse document order."""
        return list(reversed(documents))

    def _restructure_random(self, documents: List) -> List:
        """Random shuffling (control condition)."""
        import random
        docs = documents.copy()
        random.shuffle(docs)
        return docs

    def _estimate_relevance(self, documents: List, query: str) -> List[float]:
        """
        Estimate relevance of each document to the query.

        Uses simple keyword overlap if no LLM available,
        otherwise can use LLM-based relevance estimation.
        """
        if self.llm_client is None:
            # Simple keyword-based relevance
            return self._keyword_relevance(documents, query)
        else:
            # LLM-based relevance (more expensive but more accurate)
            return self._llm_relevance(documents, query)

    def _keyword_relevance(self, documents: List, query: str) -> List[float]:
        """
        Simple keyword overlap-based relevance scoring.
        """
        query_words = set(query.lower().split())

        scores = []
        for doc in documents:
            doc_words = set(doc.content.lower().split())
            overlap = len(query_words & doc_words)
            # Normalize by document length
            score = overlap / len(doc_words) if doc_words else 0
            scores.append(score)

        return scores

    def _llm_relevance(self, documents: List, query: str) -> List[float]:
        """
        Use LLM to estimate relevance (more accurate but slower).
        """
        scores = []

        for doc in documents:
            prompt = f"""Rate the relevance of this document to the question on a scale of 0-10.

Question: {query}

Document: {doc.content[:500]}...

Respond with ONLY a number between 0 and 10."""

            response = self.llm_client.generate(prompt, max_tokens=10)

            try:
                score = float(response.text.strip()) / 10.0
            except ValueError:
                score = 0.5  # Default if parsing fails

            scores.append(score)

        return scores


class SmartRestructuringStrategy:
    """
    Advanced restructuring that considers both query relevance
    and known dead zones.
    """

    def __init__(self, llm_client=None, dead_zone_map=None):
        self.llm_client = llm_client
        # Dead zone map: positions with low attention (e.g., [0.4, 0.5, 0.6])
        self.dead_zone_positions = dead_zone_map or [0.4, 0.5, 0.6]

    def restructure(self, documents: List, query: str) -> List:
        """
        Optimize document placement based on relevance and dead zones.

        Strategy:
        1. Score documents by relevance
        2. Identify safe zones (non-dead-zone positions)
        3. Place high-relevance docs in safe zones
        4. Place low-relevance docs in dead zones
        """
        # Estimate relevance
        relevance_scores = self._estimate_relevance(documents, query)

        # Create (document, relevance) pairs
        doc_relevance = list(zip(documents, relevance_scores, range(len(documents))))
        doc_relevance.sort(key=lambda x: x[1], reverse=True)

        # Determine safe and dead zone indices
        num_docs = len(documents)
        dead_zone_indices = self._get_dead_zone_indices(num_docs)
        safe_zone_indices = [i for i in range(num_docs) if i not in dead_zone_indices]

        # Place documents
        restructured = [None] * num_docs

        # Place high-relevance documents in safe zones
        for i, safe_idx in enumerate(safe_zone_indices):
            if i < len(doc_relevance):
                restructured[safe_idx] = doc_relevance[i][0]

        # Place remaining low-relevance documents in dead zones
        remaining_docs = doc_relevance[len(safe_zone_indices):]
        for i, dead_idx in enumerate(dead_zone_indices):
            if i < len(remaining_docs):
                restructured[dead_idx] = remaining_docs[i][0]

        # Fill any None slots
        restructured = [doc for doc in restructured if doc is not None]

        return restructured

    def _get_dead_zone_indices(self, num_docs: int) -> List[int]:
        """Get document indices that fall in dead zones."""
        dead_indices = []
        for pos in self.dead_zone_positions:
            idx = int(pos * num_docs)
            dead_indices.append(idx)
        return dead_indices

    def _estimate_relevance(self, documents: List, query: str) -> List[float]:
        """Estimate relevance scores."""
        query_words = set(query.lower().split())

        scores = []
        for doc in documents:
            doc_words = set(doc.content.lower().split())
            overlap = len(query_words & doc_words)
            score = overlap / len(doc_words) if doc_words else 0
            scores.append(score)

        return scores
