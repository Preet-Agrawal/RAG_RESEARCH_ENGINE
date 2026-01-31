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

from src.core.llm_client import LLMClient
from dotenv import load_dotenv

load_dotenv()


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

    def apply_combined_strategy(self, chunks: List[TextChunk], query: str) -> str:
        """
        Combines multiple strategies for best middle content recovery:
        1. Relevance-based restructuring
        2. Attention anchoring with section markers
        3. Question injection throughout
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
{detail_instruction}"""
        }
        return prompts.get(strategy, prompts["baseline"])


def summarize_document(pdf_text: str) -> Dict[str, Any]:
    """
    Summarize all chunks of the document with special focus on middle content.
    This helps understand the full document before asking questions.
    """
    import time
    start_time = time.time()

    try:
        client = LLMClient(
            provider="groq",
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            api_key=os.getenv("GROQ_API_KEY")
        )

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


def get_llm_client(provider: str = "groq", model: str = None) -> LLMClient:
    """
    Get LLM client for specified provider.
    Supports: groq, openai, anthropic
    """
    provider_configs = {
        "groq": {
            "model": model or "llama-3.3-70b-versatile",
            "api_key": os.getenv("GROQ_API_KEY"),
            "provider": "groq"
        },
        "openai": {
            "model": model or "gpt-4o",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "provider": "openai"
        },
        "anthropic": {
            "model": model or "claude-sonnet-4-20250514",
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "provider": "anthropic"
        }
    }

    config = provider_configs.get(provider, provider_configs["groq"])
    return LLMClient(
        provider=config["provider"],
        model=config["model"],
        temperature=0.1,
        api_key=config["api_key"]
    )


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
            "combined": "Applied multiple recovery strategies for best middle-content retrieval",
            "combined (fallback)": "Chunked reading found no relevant info, fell back to combined strategy"
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
        "chunked_reading",
        "combined"
    ]

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
        result = answer_question(pdf_text, question, strategy)
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
    else:
        print(json.dumps({"error": f"Unknown action: {action}. Valid actions: summarize, ask, compare, benchmark"}))
        sys.exit(1)

    # Output JSON result
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
