#!/usr/bin/env python3
"""
Process PDF and answer questions using RAG with Groq.
This integrates with the web interface.
"""
import sys
import json
import os
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.llm_client import LLMClient
from dotenv import load_dotenv

load_dotenv()


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


def answer_question(pdf_text: str, question: str) -> Dict[str, Any]:
    """Answer question using RAG with the PDF text."""
    try:
        # Initialize Groq client
        client = LLMClient(
            provider="groq",
            model="llama-3.1-8b-instant",
            temperature=0.0,
            api_key=os.getenv("GROQ_API_KEY")
        )

        # Create prompt
        prompt = f"""You are a helpful assistant analyzing a PDF document. Answer the question based ONLY on the document content below.

Document Content:
{pdf_text[:5000]}  # Limit context to stay within token limits

Question: {question}

Provide a clear, concise answer. If the answer is not in the document, say so."""

        # Get response
        response = client.generate(prompt)

        return {
            "answer": response.text,
            "sources": ["PDF Document"],
            "confidence": 0.85,
            "positions": [],
            "latency": response.latency,
        }

    except Exception as e:
        return {
            "answer": f"Error processing question: {str(e)}",
            "sources": [],
            "confidence": 0.0,
            "positions": [],
        }


def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            "error": "Usage: process_pdf.py <pdf_path> <question>"
        }))
        sys.exit(1)

    pdf_path = sys.argv[1]
    question = sys.argv[2]

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

    # Answer the question
    result = answer_question(pdf_text, question)

    # Output JSON result
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
