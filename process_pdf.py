#!/usr/bin/env python3
"""
Process PDF and answer questions using RAG with Lost-in-the-Middle recovery strategies.
All processing happens via web interface - no CLI needed.
"""
import sys
import json
import os
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.llm_client import LLMClient, ResilientLLMClient
from dotenv import load_dotenv

try:
    from src.para import PARARetriever, semantic_chunk_text
    PARA_AVAILABLE = True
except ImportError:
    PARA_AVAILABLE = False

load_dotenv(Path(__file__).parent / ".env")


@dataclass
class TextChunk:
    """Represents a chunk of text from the PDF."""
    content: str
    doc_id: str
    position: float  # 0.0 to 1.0 indicating position in document


class MiddleRecoveryProcessor:
    """
    Processor that applies strategies to recover information from the middle of documents.
    This addresses the "Lost in the Middle" phenomenon in LLMs.
    """

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[TextChunk]:
        """Split text into overlapping chunks with position tracking."""
        words = text.split()
        chunks = []
        total_words = len(words)

        i = 0
        chunk_id = 0
        while i < total_words:
            end = min(i + chunk_size, total_words)
            chunk_words = words[i:end]
            chunk_content = " ".join(chunk_words)

            # Calculate position (0.0 = start, 1.0 = end)
            position = i / total_words if total_words > 0 else 0

            chunks.append(TextChunk(
                content=chunk_content,
                doc_id=f"chunk_{chunk_id}",
                position=position
            ))

            chunk_id += 1
            i += chunk_size - overlap

        return chunks

    def apply_attention_anchoring(self, chunks: List[TextChunk], query: str) -> str:
        """
        Apply attention anchoring to emphasize middle content.
        Uses section markers, explicit instructions, and question injection.
        """
        parts = []
        num_chunks = len(chunks)
        mid_point = num_chunks // 2

        # Opening instruction
        parts.append(f"TASK: Find information to answer: {query}")
        parts.append("READ ALL SECTIONS CAREFULLY - THE ANSWER MAY BE IN THE MIDDLE SECTIONS.")
        parts.append("=" * 50)

        for i, chunk in enumerate(chunks):
            # Section marker with position info
            section_num = i + 1
            marker = f"\n{'=' * 50}\nSECTION {section_num}/{num_chunks}"

            # Special emphasis for middle sections (where LLMs typically lose attention)
            if abs(i - mid_point) <= max(1, num_chunks // 4):
                marker += " [CRITICAL - READ CAREFULLY]"

            marker += f"\n{'=' * 50}\n"
            parts.append(marker)
            parts.append(chunk.content)

            # Inject question reminder in middle
            if i == mid_point:
                parts.append(f"\n>> REMINDER: Looking for answer to: {query} <<\n")

        # Final reminder
        parts.append("\n" + "=" * 50)
        parts.append(f"NOW ANSWER: {query}")
        parts.append("=" * 50)

        return "\n".join(parts)

    def _compute_relevance_score(self, query: str, text: str) -> float:
        """
        Compute relevance score using multiple signals:
        - Exact keyword matches
        - Partial word matches (for variations)
        - Phrase proximity bonus
        """
        import re

        query_lower = query.lower()
        text_lower = text.lower()

        # Extract query words (remove common stopwords)
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                     'should', 'may', 'might', 'must', 'shall', 'can', 'of', 'to', 'in',
                     'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through',
                     'during', 'before', 'after', 'above', 'below', 'between', 'under',
                     'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where',
                     'why', 'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some',
                     'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
                     'too', 'very', 'just', 'and', 'but', 'if', 'or', 'because', 'until',
                     'while', 'what', 'which', 'who', 'this', 'that', 'these', 'those'}

        query_words = [w for w in re.findall(r'\w+', query_lower) if w not in stopwords and len(w) > 2]

        if not query_words:
            return 0.0

        score = 0.0

        # Exact word matches (highest weight)
        for word in query_words:
            if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                score += 3.0
            # Partial match (word stem appears)
            elif len(word) > 4 and word[:4] in text_lower:
                score += 1.0

        # Bonus for multiple query words appearing close together
        words_found = sum(1 for w in query_words if w in text_lower)
        if words_found >= 2:
            score += words_found * 0.5

        # Normalize by query length
        max_possible = len(query_words) * 4.0
        return min(score / max_possible, 1.0) if max_possible > 0 else 0.0

    def apply_relevance_restructuring(self, chunks: List[TextChunk], query: str) -> str:
        """
        Restructure chunks to place likely-relevant content at edges (start/end).
        Less relevant content goes to the middle where attention is lower.
        """
        # Score relevance using improved keyword matching
        scored_chunks = []
        for chunk in chunks:
            score = self._compute_relevance_score(query, chunk.content)
            scored_chunks.append((chunk, score))

        # Sort by relevance (descending)
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        # Place high-relevance at edges, low-relevance in middle
        restructured = [None] * len(chunks)
        left_idx = 0
        right_idx = len(chunks) - 1

        for i, (chunk, score) in enumerate(scored_chunks):
            if i % 2 == 0:
                restructured[left_idx] = chunk
                left_idx += 1
            else:
                restructured[right_idx] = chunk
                right_idx -= 1

        # Build context with restructured order
        parts = [f"Question: {query}\n\nDocuments (organized by relevance):\n"]
        for i, chunk in enumerate(restructured):
            if chunk:
                parts.append(f"\n[Section {i+1}]\n{chunk.content}\n")

        return "\n".join(parts)

    def apply_chunked_reading(self, chunks: List[TextChunk], query: str) -> str:
        """
        Process chunks iteratively, extracting relevant info from each.
        This avoids the middle attention problem by processing smaller segments.
        """
        extracted_info = []
        chunk_size = 3  # Process 3 chunks at a time

        for i in range(0, len(chunks), chunk_size):
            batch = chunks[i:i + chunk_size]
            batch_text = "\n\n".join([c.content for c in batch])

            extraction_prompt = f"""Read these document sections and extract ONLY information relevant to answering:
Question: {query}

Sections:
{batch_text}

If relevant information is found, state it clearly. If not, say "No relevant information in this section."

Relevant information:"""

            response = self.llm_client.generate(extraction_prompt, max_tokens=1000)
            info = response.text.strip()

            if info and "no relevant information" not in info.lower():
                extracted_info.append(f"From sections {i+1}-{min(i+chunk_size, len(chunks))}: {info}")

        if not extracted_info:
            return None  # Fall back to other method

        return "\n\n".join(extracted_info)

    def apply_query_aware_compression(self, chunks: List[TextChunk], query: str) -> str:
        """
        Query-Aware Compression (Approach 4 from research):
        - Compress/summarize irrelevant chunks to save tokens
        - Keep relevant chunks in full
        - Place full chunks at attention-rich positions (edges)
        """
        # Score all chunks for relevance
        scored_chunks = []
        for chunk in chunks:
            score = self._compute_relevance_score(query, chunk.content)
            scored_chunks.append((chunk, score))

        # Determine threshold for "relevant" (top 40%)
        scores = [s for _, s in scored_chunks]
        if scores:
            threshold = sorted(scores, reverse=True)[min(len(scores) - 1, len(scores) * 2 // 5)]
        else:
            threshold = 0.5

        # Separate into relevant (keep full) and less relevant (compress)
        relevant_chunks = [(c, s) for c, s in scored_chunks if s >= threshold]
        less_relevant_chunks = [(c, s) for c, s in scored_chunks if s < threshold]

        # Compress less relevant chunks
        compressed_summaries = []
        if less_relevant_chunks:
            # Batch compress for efficiency
            batch_size = 5
            for i in range(0, len(less_relevant_chunks), batch_size):
                batch = less_relevant_chunks[i:i + batch_size]
                batch_text = "\n\n".join([f"[Section at {int(c.position*100)}%]: {c.content[:500]}" for c, _ in batch])

                compress_prompt = f"""Compress these document sections into brief summaries (1-2 sentences each).
Keep any information that might relate to: {query}

{batch_text}

Compressed summaries:"""

                response = self.llm_client.generate(compress_prompt, max_tokens=400)
                compressed_summaries.append(response.text.strip())

        # Build final context: relevant at edges, compressed in middle
        parts = []
        parts.append(f"QUERY: {query}")
        parts.append("=" * 60)
        parts.append("\n[HIGH RELEVANCE SECTIONS - FULL TEXT]\n")

        # Add relevant chunks at start
        for i, (chunk, score) in enumerate(relevant_chunks[:len(relevant_chunks)//2 + 1]):
            parts.append(f"\n--- RELEVANT SECTION (Position: {int(chunk.position*100)}%, Score: {score:.2f}) ---")
            parts.append(chunk.content)

        # Add compressed middle
        if compressed_summaries:
            parts.append("\n\n[COMPRESSED BACKGROUND SECTIONS]\n")
            parts.append("\n".join(compressed_summaries))

        # Add remaining relevant chunks at end
        parts.append("\n\n[MORE RELEVANT SECTIONS]\n")
        for chunk, score in relevant_chunks[len(relevant_chunks)//2 + 1:]:
            parts.append(f"\n--- RELEVANT SECTION (Position: {int(chunk.position*100)}%, Score: {score:.2f}) ---")
            parts.append(chunk.content)

        parts.append("\n" + "=" * 60)
        parts.append(f"Answer the question using the relevant sections above: {query}")

        return "\n".join(parts)

    def apply_query_aware_contextualization(self, chunks: List[TextChunk], query: str) -> str:
        """
        Query-Aware Contextualization (from Liu et al. 2023 paper):
        Places the query BEFORE and AFTER the documents to enable
        query-aware processing of all document positions.

        Key finding: This dramatically improves key-value retrieval
        and slightly improves multi-document QA for first positions.
        """
        parts = []

        # Query BEFORE documents (enables query-aware contextualization)
        parts.append(f"QUESTION TO ANSWER: {query}")
        parts.append("\nRead all the following document sections to find the answer:\n")
        parts.append("=" * 60)

        # All document sections
        for i, chunk in enumerate(chunks):
            section_num = i + 1
            position_pct = int(chunk.position * 100)
            parts.append(f"\n[Document Section {section_num}/{len(chunks)} - Position: {position_pct}%]")
            parts.append(chunk.content)

        parts.append("\n" + "=" * 60)

        # Query AFTER documents (standard position)
        parts.append(f"\nBased on ALL the document sections above, answer this question:")
        parts.append(f"QUESTION: {query}")
        parts.append("\nProvide a detailed answer using information from any section:")

        return "\n".join(parts)

    def apply_combined_strategy(self, chunks: List[TextChunk], query: str) -> str:
        """
        Combines multiple strategies for best middle content recovery:
        1. Query-aware contextualization (query before AND after)
        2. Relevance-based restructuring
        3. Attention anchoring with section markers
        4. Question injection throughout
        """
        # Score using improved relevance computation
        scored_chunks = []
        for chunk in chunks:
            score = self._compute_relevance_score(query, chunk.content)
            scored_chunks.append((chunk, score))

        # Sort: highest relevance first, then by original position
        scored_chunks.sort(key=lambda x: (-x[1], x[0].position))

        parts = []
        num_chunks = len(chunks)

        # System instruction
        parts.append("INSTRUCTIONS: Read ALL sections carefully. The answer may be ANYWHERE in the document.")
        parts.append(f"QUESTION: {query}")
        parts.append("=" * 60)

        for i, (chunk, score) in enumerate(scored_chunks):
            section_num = i + 1

            # Mark potentially relevant sections
            relevance_marker = ""
            if score > 0:
                relevance_marker = " [POTENTIALLY RELEVANT]"

            # Section header
            parts.append(f"\n--- SECTION {section_num}/{num_chunks}{relevance_marker} ---")
            parts.append(chunk.content)

            # Periodic question reminders
            if (i + 1) % 3 == 0 and i < num_chunks - 1:
                parts.append(f"\n[Remember: {query}]\n")

        parts.append("\n" + "=" * 60)
        parts.append(f"Based on ALL sections above, answer: {query}")

        return "\n".join(parts)

    def apply_reranking(self, chunks: List[TextChunk], query: str) -> str:
        """
        Reranking Prompt: Place most relevant docs first and last.
        Strategic placement exploits primacy and recency bias in LLMs.
        """
        # Score all chunks
        scored_chunks = []
        for chunk in chunks:
            score = self._compute_relevance_score(query, chunk.content)
            scored_chunks.append((chunk, score))

        # Sort by relevance descending
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        # Rerank: most relevant at start, second most relevant at end, least relevant in middle
        reranked = []
        for i, (chunk, score) in enumerate(scored_chunks):
            if i % 2 == 0:
                reranked.insert(len(reranked) // 2 if i > 0 else 0, (chunk, score))
            else:
                reranked.append((chunk, score))

        # Actually do proper first/last placement:
        # Top half goes to edges (alternating start/end), bottom half fills middle
        sorted_by_relevance = sorted(scored_chunks, key=lambda x: x[1], reverse=True)
        n = len(sorted_by_relevance)
        result = [None] * n
        left, right = 0, n - 1
        for i, item in enumerate(sorted_by_relevance):
            if i % 2 == 0:
                result[left] = item
                left += 1
            else:
                result[right] = item
                right -= 1

        parts = []
        parts.append(f"You are a helpful assistant. Answer the question using ONLY the provided context.")
        parts.append(f"\nIMPORTANT: Pay equal attention to ALL context passages below, regardless of their position.\n")
        parts.append(f"Context (ordered by relevance):")

        for i, (chunk, score) in enumerate(result):
            parts.append(f"\n---\n[Passage {i+1}]")
            parts.append(chunk.content)

        parts.append(f"\n---\n")
        parts.append(f"Question: {query}")
        parts.append(f"\nBefore answering, identify which specific passages contain relevant information by quoting them. Then synthesize your answer.")

        return "\n".join(parts)

    def apply_chunk_by_chunk_reasoning(self, chunks: List[TextChunk], query: str) -> str:
        """
        Chunk-by-Chunk Reasoning: Force per-chunk evaluation before synthesis.
        The model must evaluate EACH passage individually, then combine insights.
        """
        parts = []
        parts.append(f"Given the following {len(chunks)} retrieved passages, answer the user's question.\n")
        parts.append("Passages:")

        for i, chunk in enumerate(chunks):
            parts.append(f"\n[Passage {i+1}] (Position: {int(chunk.position * 100)}% through document)")
            parts.append(chunk.content)

        parts.append(f"\n{'=' * 50}")
        parts.append("Instructions:")
        parts.append("1. First, evaluate EACH passage individually and note if it's relevant to the question.")
        parts.append("2. Then, combine insights from ALL relevant passages.")
        parts.append("3. Cite passage numbers in your answer (e.g., [Passage 3]).")
        parts.append(f"\nQuestion: {query}")

        return "\n".join(parts)

    def apply_map_reduce(self, chunks: List[TextChunk], query: str) -> str:
        """
        Map-Reduce Style: Extract relevant facts per chunk (map), then combine (reduce).
        This is the most thorough approach for large documents.
        Returns None to signal that answer_question should handle the two-phase flow.
        """
        # MAP phase: extract facts from each chunk
        all_facts = []
        batch_size = 4

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_text = "\n\n".join([
                f"[Passage {i + j + 1}]: {c.content}"
                for j, c in enumerate(batch)
            ])

            map_prompt = f"""Given these passages, extract any facts relevant to: "{query}"

{batch_text}

For each passage, write relevant facts or "NONE". Be specific and include numbers, names, and details.

Relevant facts:"""

            response = self.llm_client.generate(map_prompt, max_tokens=800)
            extracted = response.text.strip()

            if extracted and "none" not in extracted.lower()[:20]:
                all_facts.append(f"From passages {i+1}-{min(i+batch_size, len(chunks))}:\n{extracted}")

        if not all_facts:
            return None  # Signal to fallback

        # REDUCE phase: combine all extracted facts
        aggregated = "\n\n".join(all_facts)
        return aggregated

    def chunk_text_semantic(self, text: str) -> List[TextChunk]:
        """
        Semantic chunking — splits at topic boundaries using embedding similarity
        instead of fixed word count. Preserves meaning within chunks.
        """
        if not PARA_AVAILABLE:
            return self.chunk_text(text)

        para_chunks = semantic_chunk_text(text)
        return [
            TextChunk(content=c.content, doc_id=c.doc_id, position=c.position)
            for c in para_chunks
        ]

    def apply_para(self, chunks: List[TextChunk], query: str,
                    alpha: float = 0.7, beta: float = 0.3, gamma: float = None,
                    top_k: int = 10, full_text: str = None):
        """
        Position-Aware Retrieval Augmentation (PARA) — Enhanced.

        Features:
          - Semantic embeddings (all-MiniLM-L6-v2)
          - Adaptive gamma (scales with document length)
          - Multi-granularity retrieval (sentence + paragraph + section)
          - Cross-encoder reranking for top results

        Returns: (context_string, confidence_from_semantic_similarity)
        """
        if not PARA_AVAILABLE:
            raise ImportError(
                "PARA requires sentence-transformers. "
                "Install with: pip install sentence-transformers"
            )

        from src.para import TextChunk as PARAChunk
        para_chunks = [
            PARAChunk(content=c.content, doc_id=c.doc_id, position=c.position)
            for c in chunks
        ]

        retriever = PARARetriever()
        context, avg_semantic_sim = retriever.build_para_context(
            query, para_chunks, top_k=top_k, alpha=alpha, beta=beta,
            gamma=gamma, use_cross_encoder=True, full_text=full_text,
        )
        return context, avg_semantic_sim

    def get_system_prompt(self, strategy: str) -> str:
        """Get appropriate system prompt for the strategy."""
        detail_instruction = """

RESPONSE QUALITY REQUIREMENTS:
- Provide DETAILED, COMPREHENSIVE answers with specific facts, numbers, and examples from the document
- Include ALL relevant information found, not just a summary
- Quote or paraphrase specific passages when helpful
- If multiple relevant points exist, list them all
- Structure longer answers with clear organization
- Never give vague or one-sentence answers when more detail is available"""

        prompts = {
            "baseline": f"""You are an expert research assistant. Answer questions based on the provided document content.
{detail_instruction}""",

            "attention_anchoring": f"""You are an expert research assistant analyzing a document. CRITICAL INSTRUCTIONS:
1. Read ALL sections from beginning to END with equal attention
2. Pay SPECIAL attention to MIDDLE sections - they often contain crucial details
3. The answer might be ANYWHERE in the document - scan thoroughly
4. Before answering, mentally confirm you checked the middle sections carefully
5. Extract ALL relevant details, not just the first match you find
{detail_instruction}""",

            "relevance_restructuring": f"""You are an expert research assistant. The document sections have been reorganized with potentially relevant content near the start and end. However, CHECK ALL SECTIONS thoroughly as relevant information may still be elsewhere.
{detail_instruction}""",

            "chunked_reading": f"""You are an expert research assistant. You will receive extracted information from different parts of a document. Synthesize ALL this information to provide a complete, detailed answer. Do not omit any relevant details.
{detail_instruction}""",

            "combined": f"""You are an expert research assistant designed to overcome the "Lost in the Middle" problem.
CRITICAL: LLMs tend to ignore middle content. To counter this:
1. Read EVERY section with equal attention - middle sections are just as important
2. Sections marked [POTENTIALLY RELEVANT] may contain the answer, but check ALL sections
3. Check middle sections TWICE before answering
4. Extract and include ALL relevant details from every part of the document
5. If multiple pieces of information are relevant, include them all
{detail_instruction}""",

            "query_aware_compression": f"""You are an expert research assistant. You are given a document where:
- HIGH RELEVANCE sections contain full text most likely to answer the question
- COMPRESSED sections contain summarized background information
- Focus primarily on the RELEVANT sections but check compressed sections for additional context
{detail_instruction}""",

            "query_aware_contextualization": f"""You are an expert research assistant. The question appears both BEFORE and AFTER the document sections.
This is the "Query-Aware Contextualization" technique from Liu et al. (2023).
- The question at the START helps you understand what to look for as you read
- Read ALL sections with equal attention regardless of their position
- The question at the END reminds you what to answer
{detail_instruction}""",

            "reranking": f"""You are a helpful assistant that answers questions using ONLY the provided context passages.
CRITICAL INSTRUCTIONS:
- Pay EQUAL attention to ALL passages regardless of their position
- The passages have been strategically ordered with the most relevant at the start and end
- Before answering, identify which specific passages contain relevant information
- Quote or cite the passage numbers when referencing information
- Synthesize information from multiple passages when applicable
{detail_instruction}""",

            "chunk_by_chunk_reasoning": f"""You are an expert research assistant that uses structured reasoning.
CRITICAL INSTRUCTIONS:
1. You MUST evaluate EACH passage individually first - state whether it is relevant or not
2. For relevant passages, extract the key facts
3. Then synthesize your final answer from ALL relevant passages
4. Always cite passage numbers in your answer (e.g., [Passage 3])
5. Do NOT skip any passage - evaluate every single one
{detail_instruction}""",

            "para": f"""You are an expert research assistant. The document sections below were retrieved using
semantic search with position-aware scoring (PARA). They are ranked by combined relevance:
semantic similarity to your question PLUS a position-bias correction that recovers
middle-document content typically missed by LLMs.

INSTRUCTIONS:
1. All retrieved sections are highly relevant — read each one carefully
2. Sections from the document middle have been boosted to counteract the known LLM attention gap
3. Synthesize information from ALL sections, not just the first or last
4. Include specific facts, numbers, and details from the retrieved content
{detail_instruction}""",

            "map_reduce": f"""You are an expert research assistant performing the REDUCE step of a map-reduce analysis.
You are given extracted facts from different parts of a document. Your job is to:
1. Review ALL the extracted facts carefully
2. Identify the most relevant and important information
3. Combine and synthesize the facts into a comprehensive answer
4. Resolve any contradictions between different sections
5. Include specific details, numbers, and names from the facts
{detail_instruction}"""
        }
        return prompts.get(strategy, prompts["baseline"])


def _build_resilient_client(
    primary: str = "groq", temperature: float = 0.1
) -> ResilientLLMClient:
    """
    Build a resilient client that tries Groq and Gemini with instant fallback.

    Behavior:
      - Tries `primary` first (Groq by default)
      - On rate-limit / quota error → instantly switches to the other provider
      - Groq chain: llama-3.3-70b → llama-3.1-8b → gemma2-9b (all via one client each)
      - Gemini chain: gemini-2.5-flash

    No artificial wait — API rejects are handled at the application level.
    """
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    clients = []

    def _add_groq():
        if not groq_key:
            return
        for model_name in GROQ_MODEL_FALLBACK:
            clients.append(LLMClient(
                provider="groq", model=model_name,
                temperature=temperature, api_key=groq_key,
                rate_limit=0.0,
            ))

    def _add_gemini():
        if not gemini_key:
            return
        for model_name in ["gemini-2.5-flash", "gemini-1.5-flash-8b"]:
            clients.append(LLMClient(
                provider="gemini", model=model_name,
                temperature=temperature, api_key=gemini_key,
                rate_limit=0.0,
            ))

    if primary == "gemini":
        _add_gemini()
        _add_groq()
    else:
        _add_groq()
        _add_gemini()

    if not clients:
        raise RuntimeError(
            "No LLM provider configured. Set GROQ_API_KEY or GEMINI_API_KEY."
        )

    return ResilientLLMClient(clients)


# Backwards-compatible alias
def _get_groq_client_with_fallback(temperature: float = 0.1):
    """Kept for any external callers — now returns a resilient client."""
    return _build_resilient_client(primary="groq", temperature=temperature)


def summarize_document(pdf_text: str) -> Dict[str, Any]:
    """
    Summarize all chunks of the document with special focus on middle content.
    This helps understand the full document before asking questions.
    """
    import time
    start_time = time.time()

    try:
        client = _get_groq_client_with_fallback()

        processor = MiddleRecoveryProcessor(client)
        chunks = processor.chunk_text(pdf_text, chunk_size=400, overlap=50)

        num_chunks = len(chunks)
        mid_start = num_chunks // 3
        mid_end = 2 * num_chunks // 3

        chunk_summaries = []

        for i, chunk in enumerate(chunks):
            # Determine position zone
            if i < mid_start:
                zone = "beginning"
            elif i >= mid_end:
                zone = "end"
            else:
                zone = "middle"

            # Create summary prompt - extra emphasis for middle chunks
            if zone == "middle":
                prompt = f"""Summarize this section from the MIDDLE of a document.
This is a CRITICAL section that is often overlooked. Extract ALL key information.

Section {i+1}/{num_chunks} (MIDDLE - IMPORTANT):
{chunk.content}

Provide a concise but COMPLETE summary (2-3 sentences). Include specific facts, numbers, names, or key points:"""
            else:
                prompt = f"""Summarize this section from the {zone} of a document.

Section {i+1}/{num_chunks}:
{chunk.content}

Provide a concise summary (1-2 sentences):"""

            response = client.generate(prompt, max_tokens=300)

            chunk_summaries.append({
                "chunk_id": i + 1,
                "total_chunks": num_chunks,
                "zone": zone,
                "position": round(chunk.position * 100),
                "summary": response.text.strip(),
                "is_middle": zone == "middle"
            })

        # Generate overall document summary
        all_summaries = "\n".join([f"Section {s['chunk_id']}: {s['summary']}" for s in chunk_summaries])

        overall_prompt = f"""Based on these section summaries, provide an overall document summary.
Pay SPECIAL attention to the MIDDLE sections as they contain important information.

{all_summaries}

Overall document summary (3-4 sentences covering key points from ALL sections including the middle):"""

        overall_response = client.generate(overall_prompt, max_tokens=600)

        return {
            "success": True,
            "total_chunks": num_chunks,
            "chunk_summaries": chunk_summaries,
            "overall_summary": overall_response.text.strip(),
            "middle_chunks_count": sum(1 for s in chunk_summaries if s["is_middle"]),
            "latency": time.time() - start_time
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total_chunks": 0,
            "chunk_summaries": [],
            "overall_summary": "",
            "latency": time.time() - start_time
        }


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file."""
    try:
        import PyPDF2

        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"

        return text.strip()
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"


GROQ_MODEL_FALLBACK = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]


def get_llm_client(provider: str = "groq", model: str = None):
    """
    Get an LLM client with automatic cross-provider fallback.

    For "groq" / "gemini" (the free tiers), returns a ResilientLLMClient
    that tries the preferred provider first and instantly fails over to
    the other if rate-limited/quota-exhausted — zero added latency.

    For "openai" / "anthropic", returns a single direct LLMClient since
    they are paid tiers with generous limits.
    """
    # Cross-provider resilient clients for free tiers
    if provider in ("groq", "gemini"):
        return _build_resilient_client(primary=provider)

    # Direct single-provider clients for paid APIs
    if provider == "openai":
        return LLMClient(
            provider="openai",
            model=model or "gpt-4o",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY"),
            rate_limit=0.0,
        )

    if provider == "anthropic":
        return LLMClient(
            provider="anthropic",
            model=model or "claude-sonnet-4-20250514",
            temperature=0.1,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            rate_limit=0.0,
        )

    # Default: resilient Groq-first
    return _build_resilient_client(primary="groq")


def answer_question(pdf_text: str, question: str, strategy: str = "combined",
                    provider: str = "groq", model: str = None) -> Dict[str, Any]:
    """
    Answer question using RAG with Lost-in-the-Middle recovery strategies.

    Strategies:
    - baseline: Standard approach (prone to missing middle content)
    - attention_anchoring: Uses markers and instructions to force attention
    - relevance_restructuring: Places relevant content at edges
    - query_aware_compression: Compresses irrelevant, expands relevant at edges
    - chunked_reading: Processes document in smaller chunks
    - combined: Uses all strategies together (recommended)

    Providers: groq (default), openai, anthropic
    """
    import time
    start_time = time.time()

    try:
        # Initialize client based on provider
        client = get_llm_client(provider, model)

        processor = MiddleRecoveryProcessor(client)

        # Chunk the document
        chunks = processor.chunk_text(pdf_text, chunk_size=400, overlap=50)

        # Apply strategy
        if strategy == "baseline":
            # Standard approach - just use the text directly
            context = pdf_text[:8000]
            system_prompt = processor.get_system_prompt("baseline")

        elif strategy == "attention_anchoring":
            context = processor.apply_attention_anchoring(chunks, question)
            system_prompt = processor.get_system_prompt("attention_anchoring")

        elif strategy == "relevance_restructuring":
            context = processor.apply_relevance_restructuring(chunks, question)
            system_prompt = processor.get_system_prompt("relevance_restructuring")

        elif strategy == "query_aware_compression":
            context = processor.apply_query_aware_compression(chunks, question)
            system_prompt = processor.get_system_prompt("query_aware_compression")

        elif strategy == "query_aware_contextualization":
            # From Liu et al. 2023 - query before AND after documents
            context = processor.apply_query_aware_contextualization(chunks, question)
            system_prompt = processor.get_system_prompt("query_aware_contextualization")

        elif strategy == "reranking":
            context = processor.apply_reranking(chunks, question)
            system_prompt = processor.get_system_prompt("reranking")

        elif strategy == "chunk_by_chunk_reasoning":
            context = processor.apply_chunk_by_chunk_reasoning(chunks, question)
            system_prompt = processor.get_system_prompt("chunk_by_chunk_reasoning")

        elif strategy == "map_reduce":
            # Two-phase: map (extract per chunk) then reduce (synthesize)
            extracted_facts = processor.apply_map_reduce(chunks, question)
            if extracted_facts:
                reduce_prompt = f"""Using ONLY these extracted facts from a document, answer the question: "{question}"

Extracted Facts:
{extracted_facts}

Provide a detailed, comprehensive answer. Synthesize information from all the extracted facts:"""

                response = client.generate(reduce_prompt, system_prompt=processor.get_system_prompt("map_reduce"))

                return {
                    "answer": response.text,
                    "sources": ["PDF Document"],
                    "confidence": 0.92,
                    "strategy_used": strategy,
                    "chunks_processed": len(chunks),
                    "latency": time.time() - start_time,
                    "strategy_explanation": "Map-Reduce: extracted facts per chunk, then synthesized final answer"
                }
            else:
                context = processor.apply_combined_strategy(chunks, question)
                system_prompt = processor.get_system_prompt("combined")
                strategy = "combined (fallback from map_reduce)"

        elif strategy == "chunked_reading":
            # This strategy extracts info first, then synthesizes
            extracted = processor.apply_chunked_reading(chunks, question)
            if extracted:
                final_prompt = f"""Based on the following extracted information from a document, answer this question:

Question: {question}

Extracted Information:
{extracted}

Provide a clear, complete answer:"""

                response = client.generate(final_prompt, system_prompt=processor.get_system_prompt("chunked_reading"))

                return {
                    "answer": response.text,
                    "sources": ["PDF Document"],
                    "confidence": 0.9,
                    "strategy_used": strategy,
                    "chunks_processed": len(chunks),
                    "latency": time.time() - start_time,
                    "strategy_explanation": "Document processed in chunks to avoid middle-content loss"
                }
            else:
                # Fallback to combined if chunked reading found nothing
                context = processor.apply_combined_strategy(chunks, question)
                system_prompt = processor.get_system_prompt("combined")
                strategy = "combined (fallback)"

        elif strategy == "para":
            # ── PARA: Position-Aware Retrieval Augmentation (Enhanced) ──

            # Step 1: Use semantic chunking for better chunk boundaries
            if PARA_AVAILABLE:
                semantic_chunks = processor.chunk_text_semantic(pdf_text)
                if len(semantic_chunks) >= 3:
                    chunks = semantic_chunks

            # Step 2: PARA retrieval with adaptive gamma + multi-granularity + cross-encoder
            para_context, semantic_confidence = processor.apply_para(
                chunks, question, full_text=pdf_text
            )
            context = para_context
            system_prompt = processor.get_system_prompt("para")

            if len(context) > 24000:
                context = context[:24000] + "\n\n[Document truncated for processing...]"

            prompt = f"""{context}

---
Based ONLY on the retrieved sections above, provide a DETAILED and COMPREHENSIVE answer to the question.

IMPORTANT:
- Include ALL relevant information, facts, numbers, and specific details found
- If multiple relevant points exist, list and explain each one
- Quote or reference specific passages when helpful
- If the answer is not in the retrieved sections, say "The document does not contain information to answer this question."

Question: {question}

Detailed Answer:"""

            response = client.generate(prompt, system_prompt=system_prompt)

            confidence = round(max(0.1, min(1.0, semantic_confidence)), 2)
            answer_text = response.text
            grounded = True

            # Step 3: Iterative Middle Probing — if confidence is low, re-probe middle
            if confidence < 0.4 or "not contain" in answer_text.lower():
                middle_chunks = [c for c in chunks if 0.25 <= c.position <= 0.75]
                if middle_chunks:
                    middle_context, _ = processor.apply_para(
                        middle_chunks, question, alpha=0.5, beta=0.5
                    )
                    if middle_context:
                        reprobe_prompt = f"""The previous search may have missed information in the middle of the document.
Here are sections specifically from the MIDDLE of the document:

{middle_context[:12000]}

Question: {question}

If you find relevant information, provide a detailed answer. If not, say "Not found.":"""

                        reprobe_response = client.generate(reprobe_prompt, system_prompt=system_prompt)
                        reprobe_text = reprobe_response.text

                        if "not found" not in reprobe_text.lower() and len(reprobe_text) > 30:
                            answer_text = f"{answer_text}\n\n**[Additional information recovered from middle sections]:**\n{reprobe_text}"
                            confidence = min(confidence + 0.2, 0.9)

            # Step 4: Answer Grounding Check — verify answer is supported by retrieved chunks
            if len(answer_text) > 50 and "not contain" not in answer_text.lower():
                grounding_prompt = f"""You are a fact-checker. Given the CONTEXT and the ANSWER below, check if every claim in the answer is supported by the context.

CONTEXT:
{context[:8000]}

ANSWER:
{answer_text[:2000]}

Reply with ONLY one of:
- "GROUNDED" if all claims are supported by the context
- "PARTIALLY GROUNDED" if some claims are supported but others are not
- "UNGROUNDED" if the answer contains claims not found in the context"""

                grounding_response = client.generate(grounding_prompt, max_tokens=50)
                grounding_result = grounding_response.text.strip().upper()

                if "UNGROUNDED" in grounding_result:
                    grounded = False
                    confidence = max(confidence - 0.3, 0.1)
                    answer_text += "\n\n*Note: Some claims in this answer could not be verified against the document.*"
                elif "PARTIALLY" in grounding_result:
                    confidence = max(confidence - 0.1, 0.2)

            if "not contain" in answer_text.lower() or "cannot find" in answer_text.lower():
                confidence = 0.15

            return {
                "answer": answer_text,
                "sources": ["PDF Document"],
                "confidence": confidence,
                "strategy_used": strategy,
                "chunks_processed": len(chunks),
                "latency": time.time() - start_time,
                "strategy_explanation": "PARA Enhanced: Semantic chunking + adaptive position correction + multi-granularity retrieval + cross-encoder reranking + iterative middle probing + answer grounding",
                "model_used": client.model,
                "provider": provider,
                "para_semantic_similarity": round(semantic_confidence, 4),
                "grounded": grounded,
            }

        else:  # combined (default and recommended)
            context = processor.apply_combined_strategy(chunks, question)
            system_prompt = processor.get_system_prompt("combined")

        # Limit context size for API (increased for better coverage)
        if len(context) > 24000:
            context = context[:24000] + "\n\n[Document truncated for processing...]"

        # Create prompt
        prompt = f"""{context}

---
Based ONLY on the document content above, provide a DETAILED and COMPREHENSIVE answer to the question.

IMPORTANT:
- Include ALL relevant information, facts, numbers, and specific details found in the document
- If multiple relevant points exist, list and explain each one
- Quote or reference specific passages when helpful
- Structure your answer clearly if it contains multiple parts
- If the answer is not in the document, say "The document does not contain information to answer this question."

Question: {question}

Detailed Answer:"""

        # Get response
        response = client.generate(prompt, system_prompt=system_prompt)

        # Determine confidence based on response
        confidence = 0.85
        if "not contain" in response.text.lower() or "cannot find" in response.text.lower():
            confidence = 0.3
        elif len(response.text) > 100:
            confidence = 0.9

        strategy_explanations = {
            "baseline": "Standard processing without middle-content recovery",
            "attention_anchoring": "Used section markers and attention instructions to emphasize middle content",
            "relevance_restructuring": "Reorganized content to place relevant sections at document edges",
            "query_aware_compression": "Compressed irrelevant content, expanded relevant content at attention-rich positions",
            "query_aware_contextualization": "Query placed before AND after documents (Liu et al. 2023 technique)",
            "combined": "Applied multiple recovery strategies for best middle-content retrieval",
            "combined (fallback)": "Chunked reading found no relevant info, fell back to combined strategy",
            "combined (fallback from map_reduce)": "Map-reduce found no relevant facts, fell back to combined strategy",
            "reranking": "Reranked chunks with most relevant at start and end, explicit equal-attention instructions",
            "chunk_by_chunk_reasoning": "Per-passage evaluation with citation, then synthesis from all relevant passages",
            "map_reduce": "Map-Reduce: extracted facts per chunk, then synthesized final answer",
            "para": "PARA: Semantic embedding retrieval with position-bias correction for middle-document recovery"
        }

        return {
            "answer": response.text,
            "sources": ["PDF Document"],
            "confidence": confidence,
            "strategy_used": strategy,
            "chunks_processed": len(chunks),
            "latency": time.time() - start_time,
            "strategy_explanation": strategy_explanations.get(strategy, ""),
            "model_used": client.model,
            "provider": provider
        }

    except Exception as e:
        return {
            "answer": f"Error processing question: {str(e)}",
            "sources": [],
            "confidence": 0.0,
            "strategy_used": strategy,
            "chunks_processed": 0,
            "latency": time.time() - start_time,
            "error": str(e),
            "provider": provider
        }


def compare_strategies(pdf_text: str, question: str) -> Dict[str, Any]:
    """
    Run all strategies on the same question and compare results.
    This helps identify which strategy works best for different queries.
    """
    import time
    start_time = time.time()

    strategies = [
        "baseline",
        "attention_anchoring",
        "relevance_restructuring",
        "query_aware_compression",
        "query_aware_contextualization",
        "chunked_reading",
        "combined",
    ]

    # Include PARA if sentence-transformers is available
    if PARA_AVAILABLE:
        strategies.append("para")

    results = []
    for strategy in strategies:
        result = answer_question(pdf_text, question, strategy)
        results.append({
            "strategy": strategy,
            "answer": result.get("answer", ""),
            "confidence": result.get("confidence", 0),
            "latency": result.get("latency", 0),
            "chunks_processed": result.get("chunks_processed", 0),
            "explanation": result.get("strategy_explanation", "")
        })

    # Rank by confidence
    results.sort(key=lambda x: x["confidence"], reverse=True)

    return {
        "success": True,
        "question": question,
        "comparison": results,
        "best_strategy": results[0]["strategy"] if results else None,
        "total_latency": time.time() - start_time
    }


def test_closed_book(question: str, provider: str = "groq") -> Dict[str, Any]:
    """
    Test closed-book performance (no documents provided).
    From Liu et al. 2023: Used as baseline to compare with document-augmented performance.
    """
    import time
    start_time = time.time()

    try:
        client = get_llm_client(provider)

        prompt = f"""Answer the following question using only your knowledge.
If you don't know the answer, say "I don't know."

Question: {question}

Answer:"""

        response = client.generate(prompt, max_tokens=500)

        return {
            "success": True,
            "answer": response.text.strip(),
            "latency": time.time() - start_time,
            "setting": "closed_book"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "latency": time.time() - start_time
        }


def test_oracle(pdf_text: str, question: str, provider: str = "groq") -> Dict[str, Any]:
    """
    Test oracle performance (single document that contains the answer).
    From Liu et al. 2023: Best-case scenario for comparison.
    """
    import time
    start_time = time.time()

    try:
        client = get_llm_client(provider)

        # In oracle setting, we use the full document as it would contain the answer
        prompt = f"""Read the following document and answer the question.

Document:
{pdf_text[:8000]}

Question: {question}

Answer based only on the document:"""

        response = client.generate(prompt, max_tokens=1000)

        return {
            "success": True,
            "answer": response.text.strip(),
            "latency": time.time() - start_time,
            "setting": "oracle"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "latency": time.time() - start_time
        }


def run_key_value_retrieval_test(num_pairs: int = 75, test_positions: List[float] = None) -> Dict[str, Any]:
    """
    Synthetic Key-Value Retrieval Task (Section 3 of Liu et al. 2023).

    This is a minimal testbed for basic retrieval from input context.
    - Uses JSON object with randomly-generated UUID key-value pairs
    - Tests if model can retrieve the value for a specified key
    - Measures performance at different positions in the context

    From the paper: "Although some models perform the synthetic key-value
    retrieval task perfectly, other models struggle, especially when contexts
    have 140 or 300 key-value pairs."
    """
    import time
    import uuid
    start_time = time.time()

    if test_positions is None:
        # Test at beginning, middle positions, and end
        test_positions = [0.05, 0.25, 0.40, 0.50, 0.60, 0.75, 0.95]

    # Generate random key-value pairs
    kv_pairs = {}
    keys_list = []
    for _ in range(num_pairs):
        key = str(uuid.uuid4())
        value = str(uuid.uuid4())
        kv_pairs[key] = value
        keys_list.append(key)

    results = []

    for position in test_positions:
        # Get the key at this position
        key_idx = int(len(keys_list) * position)
        key_idx = min(key_idx, len(keys_list) - 1)
        target_key = keys_list[key_idx]
        expected_value = kv_pairs[target_key]

        # Create the JSON string
        json_str = json.dumps(kv_pairs, indent=2)

        # Create the prompt (from the paper's Figure 6)
        prompt = f"""Extract the value corresponding to the specified key in the JSON object below.

JSON data:
{json_str}

Key: "{target_key}"

Corresponding value:"""

        try:
            client = get_llm_client("groq")
            response = client.generate(prompt, max_tokens=100)
            answer = response.text.strip()

            # Check if the correct value appears in the response
            found = expected_value in answer or expected_value[:8] in answer

            results.append({
                "position_percent": int(position * 100),
                "position_zone": "beginning" if position < 0.33 else ("middle" if position < 0.67 else "end"),
                "key_position": key_idx + 1,
                "found": found,
                "expected_value": expected_value[:16] + "...",
                "got_value": answer[:50] if answer else "(empty)"
            })
        except Exception as e:
            results.append({
                "position_percent": int(position * 100),
                "position_zone": "beginning" if position < 0.33 else ("middle" if position < 0.67 else "end"),
                "key_position": key_idx + 1,
                "found": False,
                "error": str(e)
            })

    # Calculate accuracy
    accuracy = sum(1 for r in results if r.get("found", False)) / len(results) if results else 0

    # Identify which zones had failures
    failed_zones = [r["position_zone"] for r in results if not r.get("found", False)]
    middle_failures = sum(1 for z in failed_zones if z == "middle")

    return {
        "success": True,
        "task": "key_value_retrieval",
        "num_pairs": num_pairs,
        "test_positions": [int(p * 100) for p in test_positions],
        "results": results,
        "summary": {
            "accuracy": round(accuracy * 100, 1),
            "total_tests": len(results),
            "found_count": sum(1 for r in results if r.get("found", False)),
            "middle_failure_count": middle_failures,
            "u_shaped_pattern": middle_failures > 0 and results[0].get("found", False) and results[-1].get("found", False)
        },
        "total_latency": time.time() - start_time,
        "paper_reference": "Section 3: Key-Value Retrieval (Liu et al. 2023)"
    }


def run_needle_benchmark(pdf_text: str, needle_fact: str = None) -> Dict[str, Any]:
    """
    Run needle-in-haystack benchmark to map the attention dead zone.
    Inserts a "needle" fact at various positions and tests retrieval.

    This implements Experiment 1 from the research plan:
    - Place needle at positions: 10%, 25%, 40%, 50%, 60%, 75%, 90%
    - Measure accuracy at each position
    - Generate U-shaped attention curve data
    """
    import time
    import random
    start_time = time.time()

    # Default needle fact if none provided
    if not needle_fact:
        needle_fact = "The secret code for the research project is ALPHA-7749-OMEGA."

    # Question to find the needle
    needle_question = "What is the secret code for the research project?"

    # Test positions (percentage through document)
    test_positions = [0.10, 0.25, 0.40, 0.50, 0.60, 0.75, 0.90]

    # Split document into words for insertion
    words = pdf_text.split()
    total_words = len(words)

    results = []

    for position in test_positions:
        # Calculate insertion point
        insert_idx = int(total_words * position)

        # Create modified text with needle inserted
        modified_words = words[:insert_idx] + [f"\n\n{needle_fact}\n\n"] + words[insert_idx:]
        modified_text = " ".join(modified_words)

        # Test with baseline (most susceptible to lost-in-middle)
        baseline_result = answer_question(modified_text, needle_question, "baseline")
        baseline_found = "7749" in baseline_result.get("answer", "") or "ALPHA" in baseline_result.get("answer", "")

        # Test with combined (our best recovery strategy)
        combined_result = answer_question(modified_text, needle_question, "combined")
        combined_found = "7749" in combined_result.get("answer", "") or "ALPHA" in combined_result.get("answer", "")

        results.append({
            "position_percent": int(position * 100),
            "position_zone": "beginning" if position < 0.33 else ("middle" if position < 0.67 else "end"),
            "baseline_found": baseline_found,
            "baseline_confidence": baseline_result.get("confidence", 0),
            "combined_found": combined_found,
            "combined_confidence": combined_result.get("confidence", 0),
            "recovery_success": combined_found and not baseline_found
        })

    # Calculate summary statistics
    baseline_accuracy = sum(1 for r in results if r["baseline_found"]) / len(results)
    combined_accuracy = sum(1 for r in results if r["combined_found"]) / len(results)

    # Identify dead zone (positions where baseline fails but combined succeeds)
    dead_zone_positions = [r["position_percent"] for r in results if r["recovery_success"]]

    return {
        "success": True,
        "needle_fact": needle_fact,
        "test_positions": [int(p * 100) for p in test_positions],
        "results": results,
        "summary": {
            "baseline_accuracy": round(baseline_accuracy * 100, 1),
            "combined_accuracy": round(combined_accuracy * 100, 1),
            "improvement": round((combined_accuracy - baseline_accuracy) * 100, 1),
            "dead_zone_positions": dead_zone_positions,
            "dead_zone_recovery_rate": len(dead_zone_positions) / max(1, sum(1 for r in results if not r["baseline_found"])) * 100 if any(not r["baseline_found"] for r in results) else 0
        },
        "total_latency": time.time() - start_time
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: process_pdf.py <pdf_path> [action] [question] [strategy]"
        }))
        sys.exit(1)

    pdf_path = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "summarize"

    # Check if PDF exists
    if not os.path.exists(pdf_path):
        print(json.dumps({
            "error": f"PDF file not found: {pdf_path}"
        }))
        sys.exit(1)

    # Extract text from PDF
    pdf_text = extract_text_from_pdf(pdf_path)

    if pdf_text.startswith("Error"):
        print(json.dumps({
            "error": pdf_text
        }))
        sys.exit(1)

    if action == "summarize":
        # Summarize all chunks
        result = summarize_document(pdf_text)
    elif action == "ask":
        # Answer a question
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Question required for 'ask' action"}))
            sys.exit(1)
        question = sys.argv[3]
        strategy = sys.argv[4] if len(sys.argv) > 4 else "combined"
        provider = sys.argv[5] if len(sys.argv) > 5 else "groq"
        result = answer_question(pdf_text, question, strategy, provider=provider)
    elif action == "compare":
        # Compare all strategies on the same question
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Question required for 'compare' action"}))
            sys.exit(1)
        question = sys.argv[3]
        result = compare_strategies(pdf_text, question)
    elif action == "benchmark":
        # Run needle-in-haystack benchmark
        needle_fact = sys.argv[3] if len(sys.argv) > 3 else None
        result = run_needle_benchmark(pdf_text, needle_fact)
    elif action == "kv_retrieval":
        # Run synthetic key-value retrieval test (Section 3 of Liu et al. 2023)
        num_pairs = int(sys.argv[3]) if len(sys.argv) > 3 else 75
        result = run_key_value_retrieval_test(num_pairs)
    else:
        print(json.dumps({"error": f"Unknown action: {action}. Valid actions: summarize, ask, compare, benchmark, kv_retrieval"}))
        sys.exit(1)

    # Output JSON result
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
