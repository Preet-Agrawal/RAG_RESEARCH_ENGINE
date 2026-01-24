"""
Experiment 1: Dead Zone Mapper

Maps the attention death zones across different context positions.
Tests the core "Lost in the Middle" hypothesis.
"""
from typing import Dict, Any, List
import numpy as np
import random

from ..core.experiment import Experiment
from ..core.llm_client import LLMClient
from ..core.document_generator import DocumentGenerator


class DeadZoneMapperExperiment(Experiment):
    """
    Map where in the context window attention dies.

    For each position in the context (10%, 25%, 40%, 50%, 60%, 75%, 90%),
    we place a needle fact and test if the LLM can retrieve it.

    Expected result: U-shaped accuracy curve (high at edges, low in middle)
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__("dead_zone_mapper", config)
        self.llm_client = None
        self.doc_generator = None
        self.needle_positions = config.get("needle_positions", [0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9])
        self.num_documents = config.get("num_documents", 20)
        self.tokens_per_doc = config.get("tokens_per_doc", 500)

    def setup(self):
        """Initialize LLM client and document generator."""
        import os
        print("Setting up Dead Zone Mapper experiment...")

        provider = self.config.get("llm_provider", "groq")

        # Load API key from environment
        api_key = None
        if provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")

        self.llm_client = LLMClient(
            provider=provider,
            model=self.config.get("llm_model", "llama3-8b-8192"),
            temperature=0.0,
            api_key=api_key
        )

        self.doc_generator = DocumentGenerator()
        print("Setup complete.")

    def run_trial(self, trial_id: int) -> Dict[str, Any]:
        """
        Run a single trial.

        For each needle position, create documents with needle at that position,
        query the LLM, and check if it retrieves the correct answer.
        """
        results_by_position = {}

        for position in self.needle_positions:
            # Generate documents with needle at this position
            needle_doc = self.doc_generator.create_needle_in_haystack(
                num_documents=self.num_documents,
                tokens_per_doc=self.tokens_per_doc,
                needle_position=position
            )

            # Construct context from all documents
            context = self._build_context(needle_doc.documents)

            # Create prompt
            prompt = self._create_prompt(context, needle_doc.question)

            # Query LLM
            response = self.llm_client.generate(prompt)

            # Check if answer is correct
            is_correct = self._check_answer(response.text, needle_doc.answer)

            results_by_position[f"pos_{position:.2f}"] = {
                "correct": is_correct,
                "predicted": response.text.strip(),
                "expected": needle_doc.answer,
                "needle_doc_index": needle_doc.needle_doc_index,
                "tokens_used": response.tokens_used,
                "latency": response.latency
            }

        # Calculate overall accuracy
        correct_count = sum(1 for v in results_by_position.values() if v["correct"])
        accuracy = correct_count / len(self.needle_positions)

        return {
            "accuracy": accuracy,
            "correct_count": correct_count,
            "total_positions": len(self.needle_positions),
            "positions": results_by_position
        }

    def _build_context(self, documents: List) -> str:
        """Build context string from documents."""
        context_parts = []
        for doc in documents:
            context_parts.append(f"Document {doc.doc_id}:\n{doc.content}\n")
        return "\n".join(context_parts)

    def _create_prompt(self, context: str, question: str) -> str:
        """Create prompt for LLM."""
        return f"""You are given a collection of documents. Answer the question based ONLY on the information in these documents.

{context}

Question: {question}

Answer with ONLY the specific answer requested (e.g., just the codename, number, or fact). Do not include explanations or extra text."""

    def _check_answer(self, response: str, expected: str) -> bool:
        """Check if response contains the expected answer."""
        response_clean = response.strip().upper()
        expected_clean = expected.strip().upper()

        # Exact match
        if expected_clean in response_clean:
            return True

        # Check if response is very close (allow for minor variations)
        if response_clean == expected_clean:
            return True

        return False

    def analyze_results(self) -> Dict[str, Any]:
        """
        Analyze results to create the attention death map.

        Returns detailed statistics about accuracy at each position.
        """
        if not self.results:
            return {}

        # Aggregate results by position
        position_accuracies = {pos: [] for pos in self.needle_positions}

        for result in self.results:
            if not result.metadata.get("success", False):
                continue

            positions_data = result.metrics.get("positions", {})
            for pos in self.needle_positions:
                key = f"pos_{pos:.2f}"
                if key in positions_data:
                    is_correct = positions_data[key]["correct"]
                    position_accuracies[pos].append(1.0 if is_correct else 0.0)

        # Calculate statistics for each position
        position_stats = {}
        for pos, accuracies in position_accuracies.items():
            if accuracies:
                position_stats[pos] = {
                    "accuracy": np.mean(accuracies),
                    "std": np.std(accuracies),
                    "count": len(accuracies),
                    "min": np.min(accuracies),
                    "max": np.max(accuracies)
                }

        # Overall statistics
        overall_accuracy = np.mean([
            result.metrics.get("accuracy", 0)
            for result in self.results
            if result.metadata.get("success", False)
        ])

        analysis = {
            "overall_accuracy": overall_accuracy,
            "position_statistics": position_stats,
            "dead_zone_detected": self._detect_dead_zone(position_stats),
            "summary": self._generate_summary(position_stats)
        }

        # Print analysis
        self._print_analysis(analysis)

        return analysis

    def _detect_dead_zone(self, position_stats: Dict) -> Dict[str, Any]:
        """Detect if there's a dead zone (U-shaped curve)."""
        positions = sorted(position_stats.keys())
        accuracies = [position_stats[pos]["accuracy"] for pos in positions]

        if len(accuracies) < 3:
            return {"detected": False, "reason": "Insufficient positions"}

        # Check for U-shape: edges higher than middle
        start_acc = np.mean(accuracies[:2])  # First two positions
        middle_acc = np.mean(accuracies[len(accuracies)//3:2*len(accuracies)//3])  # Middle third
        end_acc = np.mean(accuracies[-2:])  # Last two positions

        edge_avg = (start_acc + end_acc) / 2
        drop_percentage = ((edge_avg - middle_acc) / edge_avg * 100) if edge_avg > 0 else 0

        is_u_shaped = edge_avg > middle_acc and drop_percentage > 10

        return {
            "detected": is_u_shaped,
            "start_accuracy": start_acc,
            "middle_accuracy": middle_acc,
            "end_accuracy": end_acc,
            "drop_percentage": drop_percentage,
            "worst_position": positions[np.argmin(accuracies)],
            "worst_accuracy": np.min(accuracies)
        }

    def _generate_summary(self, position_stats: Dict) -> str:
        """Generate human-readable summary."""
        positions = sorted(position_stats.keys())
        accuracies = [position_stats[pos]["accuracy"] for pos in positions]

        best_pos = positions[np.argmax(accuracies)]
        worst_pos = positions[np.argmin(accuracies)]

        summary = f"""
Dead Zone Mapping Results:
- Best position: {best_pos:.1%} (accuracy: {max(accuracies):.1%})
- Worst position: {worst_pos:.1%} (accuracy: {min(accuracies):.1%})
- Accuracy range: {min(accuracies):.1%} - {max(accuracies):.1%}
- Average accuracy: {np.mean(accuracies):.1%}
"""
        return summary.strip()

    def _print_analysis(self, analysis: Dict[str, Any]):
        """Print analysis results."""
        print("\n" + "="*60)
        print("DEAD ZONE ANALYSIS")
        print("="*60)

        print(f"\nOverall Accuracy: {analysis['overall_accuracy']:.1%}")

        print("\nAccuracy by Position:")
        position_stats = analysis["position_statistics"]
        for pos in sorted(position_stats.keys()):
            stats = position_stats[pos]
            print(f"  {pos:4.0%}: {stats['accuracy']:6.1%} (±{stats['std']:.3f})")

        print("\nDead Zone Detection:")
        dz = analysis["dead_zone_detected"]
        if dz["detected"]:
            print(f"  ✓ Dead zone DETECTED")
            print(f"    - Start accuracy: {dz['start_accuracy']:.1%}")
            print(f"    - Middle accuracy: {dz['middle_accuracy']:.1%}")
            print(f"    - End accuracy: {dz['end_accuracy']:.1%}")
            print(f"    - Drop: {dz['drop_percentage']:.1f}%")
            print(f"    - Worst position: {dz['worst_position']:.0%} ({dz['worst_accuracy']:.1%})")
        else:
            print(f"  ✗ No clear dead zone detected")

        print("\n" + analysis["summary"])
        print("="*60 + "\n")
