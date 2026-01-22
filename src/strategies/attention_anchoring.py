"""
Strategy 3: Attention Anchoring

Insert markers, separators, and instructions to force attention to middle content.
"""
from typing import List, Dict, Any


class AttentionAnchoringStrategy:
    """
    Use various anchoring techniques to boost attention to middle content.

    Techniques:
    1. Numeric section markers
    2. Explicit attention instructions
    3. Formatting (bold, caps, separators)
    4. Redundancy (repeat key info)
    5. Question injection
    """

    def __init__(self):
        pass

    def apply_anchoring(self, documents: List, method: str = "section_markers",
                       query: str = None) -> str:
        """
        Apply attention anchoring to documents.

        Args:
            documents: List of Document objects
            method: Anchoring method to use
            query: Optional query for query-aware anchoring

        Returns:
            Context string with anchoring applied
        """
        if method == "section_markers":
            return self._apply_section_markers(documents)
        elif method == "explicit_instructions":
            return self._apply_explicit_instructions(documents)
        elif method == "formatting":
            return self._apply_formatting(documents)
        elif method == "redundancy":
            return self._apply_redundancy(documents)
        elif method == "question_injection":
            return self._apply_question_injection(documents, query)
        elif method == "combined":
            return self._apply_combined(documents, query)
        else:
            return self._baseline(documents)

    def _baseline(self, documents: List) -> str:
        """No anchoring (baseline)."""
        parts = []
        for doc in documents:
            parts.append(f"Document {doc.doc_id}:\n{doc.content}\n")
        return "\n".join(parts)

    def _apply_section_markers(self, documents: List) -> str:
        """Add prominent section markers."""
        parts = []
        for i, doc in enumerate(documents, 1):
            marker = f"\n{'='*60}\nSECTION {i} of {len(documents)}\n{'='*60}\n"
            parts.append(f"{marker}\n{doc.content}\n")
        return "\n".join(parts)

    def _apply_explicit_instructions(self, documents: List) -> str:
        """Add explicit attention instructions throughout."""
        parts = []
        mid_point = len(documents) // 2

        for i, doc in enumerate(documents):
            # Add instruction before middle documents
            if abs(i - mid_point) <= 2:
                instruction = "\n⚠️ IMPORTANT: Pay special attention to the following section ⚠️\n"
                parts.append(instruction)

            parts.append(f"Document {doc.doc_id}:\n{doc.content}\n")

        return "\n".join(parts)

    def _apply_formatting(self, documents: List) -> str:
        """Use formatting to highlight middle content."""
        parts = []
        mid_point = len(documents) // 2

        for i, doc in enumerate(documents):
            # Emphasize middle documents
            if abs(i - mid_point) <= 3:
                header = f"\n{'#'*60}\n### CRITICAL DOCUMENT {doc.doc_id} ###\n{'#'*60}\n"
                content = doc.content
                footer = f"\n{'#'*60}\n"
                parts.append(f"{header}{content}{footer}")
            else:
                parts.append(f"Document {doc.doc_id}:\n{doc.content}\n")

        return "\n".join(parts)

    def _apply_redundancy(self, documents: List) -> str:
        """Repeat middle documents at the end."""
        parts = []

        # Add all documents normally
        for doc in documents:
            parts.append(f"Document {doc.doc_id}:\n{doc.content}\n")

        # Identify and repeat middle documents
        mid_start = len(documents) // 3
        mid_end = 2 * len(documents) // 3
        middle_docs = documents[mid_start:mid_end]

        if middle_docs:
            parts.append("\n" + "="*60)
            parts.append("KEY SECTIONS (REPEATED FOR EMPHASIS)")
            parts.append("="*60 + "\n")

            for doc in middle_docs:
                parts.append(f"Document {doc.doc_id} (REPEATED):\n{doc.content}\n")

        return "\n".join(parts)

    def _apply_question_injection(self, documents: List, query: str) -> str:
        """Inject the question at multiple points."""
        if not query:
            return self._baseline(documents)

        parts = []
        injection_points = [0, len(documents) // 3, 2 * len(documents) // 3, len(documents) - 1]

        for i, doc in enumerate(documents):
            if i in injection_points:
                parts.append(f"\n📌 REMINDER: We are looking for: {query}\n")

            parts.append(f"Document {doc.doc_id}:\n{doc.content}\n")

        # Add final reminder
        parts.append(f"\n📌 FINAL REMINDER: Answer this question: {query}\n")

        return "\n".join(parts)

    def _apply_combined(self, documents: List, query: str) -> str:
        """Combine multiple anchoring techniques."""
        parts = []
        mid_point = len(documents) // 2

        # Opening instruction
        if query:
            parts.append(f"TASK: Find information to answer: {query}\n")
            parts.append("READ ALL SECTIONS CAREFULLY, ESPECIALLY THE MIDDLE SECTIONS.\n")
            parts.append("="*60 + "\n")

        for i, doc in enumerate(documents, 1):
            # Section marker
            marker = f"\n{'='*60}\nSECTION {i}/{len(documents)}"

            # Special emphasis for middle
            if abs(i - mid_point - 1) <= 2:
                marker += " ⚠️ CRITICAL SECTION ⚠️"

            marker += f"\n{'='*60}\n"

            parts.append(marker)
            parts.append(doc.content)
            parts.append("\n")

        # Reminder at end
        if query:
            parts.append("\n" + "="*60)
            parts.append(f"Remember to answer: {query}")
            parts.append("="*60 + "\n")

        return "".join(parts)

    def create_system_prompt(self, method: str = "standard") -> str:
        """
        Create system prompt that encourages attention to all content.

        Args:
            method: Type of system prompt

        Returns:
            System prompt string
        """
        prompts = {
            "standard": "You are a helpful assistant. Answer questions based on the provided documents.",

            "attention_emphasized": """You are a helpful assistant. When answering questions:
1. Read ALL documents carefully from beginning to end
2. Pay EQUAL attention to documents in the middle, not just the first and last
3. The answer might be anywhere in the context
4. If you're unsure, reread the middle sections""",

            "position_aware": """You are a helpful assistant. IMPORTANT:
- Information can appear ANYWHERE in the documents
- The MIDDLE documents are just as important as the first and last
- Do not assume information at the start or end is more relevant
- Systematically check all sections before answering""",

            "explicit_middle": """You are a helpful assistant. CRITICAL INSTRUCTION:
Research shows that AI systems often miss information in the middle of long contexts.
To counter this:
1. Read the ENTIRE context, paying special attention to middle sections
2. The answer is equally likely to be in early, middle, or late documents
3. After reading, explicitly ask yourself: "Did I check the middle thoroughly?"
4. Only answer when you're confident you've read everything"""
        }

        return prompts.get(method, prompts["standard"])
