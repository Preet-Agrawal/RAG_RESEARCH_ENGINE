"""
Strategy 2: Chunked Iterative Reading

Instead of processing all documents at once, read in strategic chunks.
Like how humans read long documents section-by-section.
"""
from typing import List, Dict, Any


class ChunkedReadingStrategy:
    """
    Process documents in chunks rather than all at once.

    Strategies:
    1. Sequential chunks: Read chunks one by one
    2. Hierarchical: First pass extracts key info, second pass dives deep
    3. Query-guided: Only read chunks that seem relevant
    """

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def process(self, documents: List, query: str, method: str = "sequential",
                chunk_size: int = 5) -> str:
        """
        Process documents using chunked reading.

        Args:
            documents: List of documents
            query: Question to answer
            method: 'sequential', 'hierarchical', or 'query_guided'
            chunk_size: Number of documents per chunk

        Returns:
            Final answer
        """
        if method == "sequential":
            return self._sequential_chunks(documents, query, chunk_size)
        elif method == "hierarchical":
            return self._hierarchical_chunks(documents, query, chunk_size)
        elif method == "query_guided":
            return self._query_guided_chunks(documents, query, chunk_size)
        else:
            return self._baseline_full_context(documents, query)

    def _sequential_chunks(self, documents: List, query: str, chunk_size: int) -> str:
        """
        Read documents in sequential chunks, extracting information from each.

        Process:
        1. Divide documents into chunks
        2. For each chunk, extract relevant information
        3. Combine extracted information
        4. Generate final answer
        """
        # Divide into chunks
        chunks = [documents[i:i+chunk_size] for i in range(0, len(documents), chunk_size)]

        # Extract from each chunk
        extracted_info = []

        for i, chunk in enumerate(chunks):
            chunk_context = self._build_chunk_context(chunk)

            extraction_prompt = f"""Read these documents and extract any information relevant to answering this question:

Question: {query}

Documents:
{chunk_context}

Extract ONLY relevant information. If no relevant information is found, respond with "No relevant information."

Relevant information:"""

            response = self.llm_client.generate(extraction_prompt)
            info = response.text.strip()

            if info and info != "No relevant information.":
                extracted_info.append(f"From chunk {i+1}: {info}")

        # Combine and answer
        if not extracted_info:
            return "Unable to find relevant information"

        combined_info = "\n".join(extracted_info)

        final_prompt = f"""Based on the extracted information below, answer this question:

Question: {query}

Extracted Information:
{combined_info}

Answer (be concise and specific):"""

        response = self.llm_client.generate(final_prompt)
        return response.text.strip()

    def _hierarchical_chunks(self, documents: List, query: str, chunk_size: int) -> str:
        """
        Two-pass hierarchical reading.

        Pass 1: Quickly scan all documents to identify relevant chunks
        Pass 2: Deep read of relevant chunks
        """
        # Pass 1: Quick scan - get summaries
        chunks = [documents[i:i+chunk_size] for i in range(0, len(documents), chunk_size)]
        chunk_summaries = []

        for i, chunk in enumerate(chunks):
            chunk_context = self._build_chunk_context(chunk)

            summary_prompt = f"""Briefly summarize the main topics in these documents (1-2 sentences):

{chunk_context}

Summary:"""

            response = self.llm_client.generate(summary_prompt, max_tokens=100)
            summary = response.text.strip()
            chunk_summaries.append((i, summary))

        # Assess which chunks are relevant
        relevance_prompt = f"""Question: {query}

Here are summaries of document chunks:

""" + "\n".join([f"Chunk {i+1}: {summary}" for i, summary in chunk_summaries]) + """

Which chunks (by number) are most likely to contain information relevant to the question?
Respond with ONLY the chunk numbers, comma-separated (e.g., "1,3,5"):"""

        response = self.llm_client.generate(relevance_prompt, max_tokens=50)

        # Parse relevant chunk indices
        try:
            relevant_indices = [int(x.strip()) - 1 for x in response.text.strip().split(",")]
        except:
            relevant_indices = list(range(len(chunks)))  # Fallback: use all

        # Pass 2: Deep read of relevant chunks
        extracted_info = []

        for idx in relevant_indices:
            if 0 <= idx < len(chunks):
                chunk = chunks[idx]
                chunk_context = self._build_chunk_context(chunk)

                extraction_prompt = f"""Read these documents carefully and extract information to answer this question:

Question: {query}

Documents:
{chunk_context}

Relevant information:"""

                response = self.llm_client.generate(extraction_prompt)
                info = response.text.strip()
                if info:
                    extracted_info.append(info)

        # Generate final answer
        if not extracted_info:
            return "Unable to find relevant information"

        combined_info = "\n".join(extracted_info)

        final_prompt = f"""Based on the extracted information, answer this question:

Question: {query}

Information:
{combined_info}

Answer:"""

        response = self.llm_client.generate(final_prompt)
        return response.text.strip()

    def _query_guided_chunks(self, documents: List, query: str, chunk_size: int) -> str:
        """
        Only read chunks that appear relevant based on quick relevance check.
        """
        chunks = [documents[i:i+chunk_size] for i in range(0, len(documents), chunk_size)]

        # Quick relevance check for each chunk
        relevant_chunks = []

        for chunk in chunks:
            # Use first document in chunk as representative
            sample_doc = chunk[0]
            sample_text = sample_doc.content[:300]  # First 300 chars

            relevance_prompt = f"""Does this text excerpt seem relevant to the question? Respond with only YES or NO.

Question: {query}

Text: {sample_text}

Relevant?"""

            response = self.llm_client.generate(relevance_prompt, max_tokens=5)

            if "YES" in response.text.upper():
                relevant_chunks.append(chunk)

        # Process only relevant chunks
        if not relevant_chunks:
            relevant_chunks = chunks[:3]  # Fallback: use first 3 chunks

        extracted_info = []
        for chunk in relevant_chunks:
            chunk_context = self._build_chunk_context(chunk)

            extraction_prompt = f"""Extract information from these documents to answer the question:

Question: {query}

Documents:
{chunk_context}

Relevant information:"""

            response = self.llm_client.generate(extraction_prompt)
            info = response.text.strip()
            if info:
                extracted_info.append(info)

        # Final answer
        combined_info = "\n".join(extracted_info)

        final_prompt = f"""Answer based on this information:

Question: {query}

Information:
{combined_info}

Answer:"""

        response = self.llm_client.generate(final_prompt)
        return response.text.strip()

    def _baseline_full_context(self, documents: List, query: str) -> str:
        """Baseline: process all documents at once (standard approach)."""
        context = self._build_chunk_context(documents)

        prompt = f"""Answer the question based on these documents:

{context}

Question: {query}

Answer:"""

        response = self.llm_client.generate(prompt)
        return response.text.strip()

    def _build_chunk_context(self, documents: List) -> str:
        """Build context string from document chunk."""
        parts = []
        for doc in documents:
            parts.append(f"Document {doc.doc_id}:\n{doc.content}\n")
        return "\n".join(parts)
