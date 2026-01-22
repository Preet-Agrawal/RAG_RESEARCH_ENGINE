"""
Generate synthetic documents for experiments.
"""
from typing import List, Dict, Tuple, Optional
import random
import string
from dataclasses import dataclass
import tiktoken


@dataclass
class Document:
    """Represents a document."""
    content: str
    doc_id: str
    metadata: Dict


@dataclass
class NeedleDocument:
    """Document with a hidden 'needle' fact."""
    documents: List[Document]
    needle_text: str
    needle_position: int
    needle_doc_index: int
    question: str
    answer: str


class DocumentGenerator:
    """Generate synthetic documents for testing."""

    def __init__(self, encoding_name: str = "cl100k_base"):
        self.encoding = tiktoken.get_encoding(encoding_name)
        self.topics = [
            "climate change", "artificial intelligence", "quantum computing",
            "space exploration", "renewable energy", "biotechnology",
            "ancient civilizations", "economic theory", "neural networks",
            "particle physics", "marine biology", "architectural design",
            "political philosophy", "Renaissance art", "cryptography"
        ]

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))

    def generate_filler_text(self, topic: str, target_tokens: int) -> str:
        """
        Generate filler text about a topic with approximately target_tokens.

        This creates realistic-looking text that serves as 'haystack' content.
        """
        templates = [
            f"The study of {topic} has evolved significantly over recent decades. "
            f"Researchers have made substantial progress in understanding various aspects of {topic}. "
            f"Current methodologies in {topic} research incorporate advanced analytical techniques. "
            f"The field continues to develop new frameworks for investigating {topic}. "
            f"Historical perspectives on {topic} provide important context for modern analysis. "
            f"Contemporary debates in {topic} often center on methodological approaches. "
            f"Interdisciplinary connections have enriched our understanding of {topic}. "
            f"Future directions in {topic} research appear promising and multifaceted. ",

            f"In the context of {topic}, several key principles have emerged. "
            f"Foundational concepts in {topic} remain relevant despite evolving technologies. "
            f"Expert practitioners of {topic} emphasize the importance of systematic approaches. "
            f"Educational programs in {topic} have expanded to meet growing demand. "
            f"The practical applications of {topic} continue to demonstrate value across sectors. "
            f"Theoretical frameworks in {topic} help organize our understanding of complex phenomena. "
            f"Recent innovations in {topic} have opened new avenues for investigation. "
            f"Collaborative efforts in {topic} research have yielded significant insights. ",

            f"The evolution of {topic} reflects broader trends in scientific inquiry. "
            f"Historical developments in {topic} inform current research directions. "
            f"Methodological rigor in {topic} studies ensures reliable findings. "
            f"Cross-disciplinary approaches enhance {topic} research outcomes. "
            f"Technical advances have transformed how we study {topic}. "
            f"The societal implications of {topic} warrant careful consideration. "
            f"Ongoing debates in {topic} highlight areas requiring further investigation. "
            f"Emerging paradigms in {topic} challenge traditional assumptions. "
        ]

        text = ""
        current_tokens = 0

        while current_tokens < target_tokens:
            template = random.choice(templates)
            text += template
            current_tokens = self.count_tokens(text)

            if current_tokens >= target_tokens:
                break

        return text.strip()

    def create_needle_fact(self) -> Tuple[str, str, str]:
        """
        Create a unique 'needle' fact with question and answer.

        Returns:
            (needle_text, question, answer)
        """
        # Generate unique identifiers
        magic_number = random.randint(10000, 99999)
        code = ''.join(random.choices(string.ascii_uppercase, k=6))
        city = random.choice([
            "Alexandria", "Babylon", "Carthage", "Damascus", "Ephesus",
            "Florence", "Geneva", "Heidelberg", "Isfahan", "Jerusalem"
        ])
        item = random.choice([
            "artifact", "manuscript", "crystal", "medallion", "compass",
            "astrolabe", "tome", "relic", "scroll", "device"
        ])

        needle_text = (
            f"The classified research project codenamed {code} was conducted in {city} "
            f"during the year {magic_number}. The project's primary focus involved "
            f"analyzing a unique {item} with unprecedented properties."
        )

        question = f"What was the codename of the classified research project conducted in {city}?"
        answer = code

        return needle_text, question, answer

    def create_needle_in_haystack(
        self,
        num_documents: int = 20,
        tokens_per_doc: int = 500,
        needle_position: float = 0.5
    ) -> NeedleDocument:
        """
        Create a set of documents with a needle fact at specified position.

        Args:
            num_documents: Number of documents to generate
            tokens_per_doc: Target tokens per document
            needle_position: Where to place needle (0.0 = start, 1.0 = end)

        Returns:
            NeedleDocument with all components
        """
        # Determine which document gets the needle
        needle_doc_index = int(needle_position * num_documents)
        needle_doc_index = max(0, min(needle_doc_index, num_documents - 1))

        # Create needle
        needle_text, question, answer = self.create_needle_fact()

        documents = []
        for i in range(num_documents):
            topic = random.choice(self.topics)

            if i == needle_doc_index:
                # This document contains the needle
                # Generate half the content, insert needle, then generate rest
                filler_tokens = tokens_per_doc - self.count_tokens(needle_text)
                half_tokens = filler_tokens // 2

                part1 = self.generate_filler_text(topic, half_tokens)
                part2 = self.generate_filler_text(topic, half_tokens)

                content = f"{part1}\n\n{needle_text}\n\n{part2}"
            else:
                # Regular filler document
                content = self.generate_filler_text(topic, tokens_per_doc)

            doc = Document(
                content=content,
                doc_id=f"doc_{i:03d}",
                metadata={
                    "topic": topic,
                    "position": i,
                    "has_needle": i == needle_doc_index
                }
            )
            documents.append(doc)

        return NeedleDocument(
            documents=documents,
            needle_text=needle_text,
            needle_position=needle_position,
            needle_doc_index=needle_doc_index,
            question=question,
            answer=answer
        )

    def create_multi_needle_document(
        self,
        num_documents: int = 20,
        tokens_per_doc: int = 500,
        num_needles: int = 3
    ) -> Dict:
        """Create documents with multiple needles for complex retrieval tasks."""
        needle_positions = [
            random.uniform(0.1, 0.9) for _ in range(num_needles)
        ]

        needles_data = []
        for pos in needle_positions:
            needle_text, question, answer = self.create_needle_fact()
            needles_data.append({
                "text": needle_text,
                "question": question,
                "answer": answer,
                "position": pos
            })

        # Sort by position
        needles_data.sort(key=lambda x: x["position"])

        documents = []
        needle_idx = 0

        for i in range(num_documents):
            topic = random.choice(self.topics)
            content = self.generate_filler_text(topic, tokens_per_doc)

            # Check if this document should contain a needle
            doc_position = i / num_documents
            has_needle = False

            if needle_idx < len(needles_data):
                needle_pos = needles_data[needle_idx]["position"]
                if abs(doc_position - needle_pos) < (1.0 / num_documents):
                    # Insert needle
                    parts = content.split(". ")
                    mid = len(parts) // 2
                    parts.insert(mid, needles_data[needle_idx]["text"])
                    content = ". ".join(parts)
                    has_needle = True
                    needle_idx += 1

            doc = Document(
                content=content,
                doc_id=f"doc_{i:03d}",
                metadata={
                    "topic": topic,
                    "position": i,
                    "has_needle": has_needle
                }
            )
            documents.append(doc)

        return {
            "documents": documents,
            "needles": needles_data
        }
