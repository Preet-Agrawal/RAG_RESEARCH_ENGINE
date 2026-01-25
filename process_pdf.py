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

    def apply_relevance_restructuring(self, chunks: List[TextChunk], query: str) -> str:
        """
        Restructure chunks to place likely-relevant content at edges (start/end).
        Less relevant content goes to the middle where attention is lower.
        """
        # Score relevance using keyword overlap
        query_words = set(query.lower().split())

        scored_chunks = []
        for chunk in chunks:
            chunk_words = set(chunk.content.lower().split())
            overlap = len(query_words & chunk_words)
            score = overlap / len(chunk_words) if chunk_words else 0
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

            response = self.llm_client.generate(extraction_prompt, max_tokens=500)
            info = response.text.strip()

            if info and "no relevant information" not in info.lower():
                extracted_info.append(f"From sections {i+1}-{min(i+chunk_size, len(chunks))}: {info}")

        if not extracted_info:
            return None  # Fall back to other method

        return "\n\n".join(extracted_info)

    def apply_combined_strategy(self, chunks: List[TextChunk], query: str) -> str:
        """
        Combines multiple strategies for best middle content recovery:
        1. Relevance-based restructuring
        2. Attention anchoring with section markers
        3. Question injection throughout
        """
        # Score and partially restructure
        query_words = set(query.lower().split())

        scored_chunks = []
        for chunk in chunks:
            chunk_words = set(chunk.content.lower().split())
            overlap = len(query_words & chunk_words)
            score = overlap / len(chunk_words) if chunk_words else 0
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
        prompts = {
            "baseline": "You are a helpful assistant. Answer questions based on the provided document content.",

            "attention_anchoring": """You are a helpful assistant analyzing a document. CRITICAL INSTRUCTIONS:
1. Read ALL sections from beginning to END
2. Pay EQUAL attention to MIDDLE sections - they are just as important
3. The answer might be ANYWHERE in the document
4. Before answering, mentally confirm you read the middle sections carefully""",

            "relevance_restructuring": """You are a helpful assistant. The document sections have been reorganized with potentially relevant content near the start and end. However, CHECK ALL SECTIONS as relevant information may still be elsewhere.""",

            "chunked_reading": """You are a helpful assistant. You will receive extracted information from different parts of a document. Synthesize this information to provide a complete answer.""",

            "combined": """You are a research assistant designed to overcome the "Lost in the Middle" problem.
CRITICAL: LLMs tend to ignore middle content. To counter this:
1. Read EVERY section with equal attention
2. Sections marked [POTENTIALLY RELEVANT] may contain the answer
3. Check middle sections TWICE before answering
4. If unsure, review the middle sections again"""
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
            model="llama-3.1-8b-instant",
            temperature=0.0,
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

            response = client.generate(prompt, max_tokens=150)

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

        overall_response = client.generate(overall_prompt, max_tokens=300)

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


def answer_question(pdf_text: str, question: str, strategy: str = "combined") -> Dict[str, Any]:
    """
    Answer question using RAG with Lost-in-the-Middle recovery strategies.

    Strategies:
    - baseline: Standard approach (prone to missing middle content)
    - attention_anchoring: Uses markers and instructions to force attention
    - relevance_restructuring: Places relevant content at edges
    - chunked_reading: Processes document in smaller chunks
    - combined: Uses all strategies together (recommended)
    """
    import time
    start_time = time.time()

    try:
        # Initialize Groq client
        client = LLMClient(
            provider="groq",
            model="llama-3.1-8b-instant",
            temperature=0.0,
            api_key=os.getenv("GROQ_API_KEY")
        )

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

        # Limit context size for API
        if len(context) > 12000:
            context = context[:12000] + "\n\n[Document truncated for processing...]"

        # Create prompt
        prompt = f"""{context}

---
Answer the question based ONLY on the document content above.
If the answer is not in the document, say "The document does not contain information to answer this question."

Question: {question}

Answer:"""

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
            "strategy_explanation": strategy_explanations.get(strategy, "")
        }

    except Exception as e:
        return {
            "answer": f"Error processing question: {str(e)}",
            "sources": [],
            "confidence": 0.0,
            "strategy_used": strategy,
            "chunks_processed": 0,
            "latency": time.time() - start_time,
            "error": str(e)
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
    else:
        print(json.dumps({"error": f"Unknown action: {action}"}))
        sys.exit(1)

    # Output JSON result
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
