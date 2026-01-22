#!/usr/bin/env python3
"""
Quick test script to verify Ollama is working correctly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.llm_client import LLMClient
from src.core.document_generator import DocumentGenerator


def test_ollama_connection():
    """Test basic Ollama connectivity."""
    print("🔍 Testing Ollama connection...")

    try:
        client = LLMClient(
            provider="ollama",
            model="llama3:8b",
            temperature=0.0
        )

        response = client.generate("Say 'Hello, Ollama is working!' and nothing else.")
        print(f"✅ Ollama is working!")
        print(f"   Response: {response.text[:100]}")
        print(f"   Latency: {response.latency:.2f}s")
        return True

    except Exception as e:
        print(f"❌ Ollama connection failed: {str(e)}")
        print("\n💡 Make sure:")
        print("   1. Ollama is installed (https://ollama.com)")
        print("   2. Ollama is running (it should auto-start)")
        print("   3. You have pulled a model: ollama pull llama3:8b")
        return False


def test_needle_retrieval():
    """Test simple needle-in-haystack retrieval."""
    print("\n🔍 Testing needle-in-haystack retrieval...")

    try:
        client = LLMClient(
            provider="ollama",
            model="llama3:8b",
            temperature=0.0
        )

        doc_gen = DocumentGenerator()

        # Create simple test case with needle at position 0.5 (middle)
        needle_doc = doc_gen.create_needle_in_haystack(
            num_documents=10,
            tokens_per_doc=200,
            needle_position=0.5
        )

        # Build context
        context = "\n\n".join([
            f"Document {doc.doc_id}:\n{doc.content}"
            for doc in needle_doc.documents
        ])

        prompt = f"""Answer based ONLY on the documents below.

{context}

Question: {needle_doc.question}

Answer with ONLY the specific answer (no explanations):"""

        print(f"   Question: {needle_doc.question}")
        print(f"   Expected answer: {needle_doc.answer}")
        print(f"   Needle position: {needle_doc.needle_position:.0%} (document {needle_doc.needle_doc_index})")

        response = client.generate(prompt)

        is_correct = needle_doc.answer.upper() in response.text.upper()

        if is_correct:
            print(f"   ✅ Correct! Model found: {response.text.strip()}")
        else:
            print(f"   ❌ Incorrect. Model said: {response.text.strip()}")
            print(f"      (This is expected at middle positions - 'Lost in the Middle'!)")

        print(f"   Latency: {response.latency:.2f}s")
        print(f"   Tokens used: ~{response.tokens_used}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False


def main():
    print("="*60)
    print("Ollama Integration Test")
    print("="*60)
    print()

    # Test 1: Basic connection
    if not test_ollama_connection():
        print("\n⚠️  Fix Ollama connection before proceeding.")
        sys.exit(1)

    # Test 2: Needle retrieval
    if not test_needle_retrieval():
        print("\n⚠️  Needle retrieval test failed.")
        sys.exit(1)

    print("\n" + "="*60)
    print("✅ All tests passed! You're ready to run experiments.")
    print("="*60)
    print()
    print("Next steps:")
    print("  1. Run a quick experiment:")
    print("     python run_experiments.py dead_zone --quick \\")
    print("       --provider ollama --model llama3:8b")
    print()
    print("  2. See OLLAMA_SETUP.md for detailed instructions")
    print()


if __name__ == "__main__":
    main()
