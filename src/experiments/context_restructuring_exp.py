"""
Experiment 2: Context Restructuring

Compare baseline (no restructuring) vs intelligent restructuring strategies.
"""
from typing import Dict, Any, List
import numpy as np

from ..core.experiment import Experiment
from ..core.llm_client import LLMClient
from ..core.document_generator import DocumentGenerator
from ..strategies.context_restructuring import ContextRestructuringStrategy


class ContextRestructuringExperiment(Experiment):
    """
    Test if intelligent context restructuring improves retrieval.

    Compares:
    - Baseline (original order)
    - Random shuffling (control)
    - Relevance-based restructuring
    - Reverse order
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__("context_restructuring", config)
        self.llm_client = None
        self.doc_generator = None
        self.restructure_strategy = None

        self.methods = ["baseline", "random", "relevance", "reverse", "alternating"]
        self.num_documents = config.get("num_documents", 20)
        self.tokens_per_doc = config.get("tokens_per_doc", 500)
        self.needle_position = 0.5  # Test with middle position (hardest)

    def setup(self):
        """Initialize components."""
        import os
        print("Setting up Context Restructuring experiment...")

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
        self.restructure_strategy = ContextRestructuringStrategy(self.llm_client)

        print("Setup complete.")

    def run_trial(self, trial_id: int) -> Dict[str, Any]:
        """
        Run trial comparing different restructuring methods.
        """
        # Generate needle document (needle in middle - hardest case)
        needle_doc = self.doc_generator.create_needle_in_haystack(
            num_documents=self.num_documents,
            tokens_per_doc=self.tokens_per_doc,
            needle_position=self.needle_position
        )

        results_by_method = {}

        for method in self.methods:
            # Apply restructuring
            if method == "baseline":
                restructured_docs = needle_doc.documents
            else:
                restructured_docs = self.restructure_strategy.restructure(
                    needle_doc.documents,
                    needle_doc.question,
                    method=method
                )

            # Build context
            context = self._build_context(restructured_docs)

            # Query LLM
            prompt = self._create_prompt(context, needle_doc.question)
            response = self.llm_client.generate(prompt)

            # Check correctness
            is_correct = self._check_answer(response.text, needle_doc.answer)

            results_by_method[method] = {
                "correct": is_correct,
                "predicted": response.text.strip(),
                "tokens_used": response.tokens_used,
                "latency": response.latency
            }

        # Calculate metrics
        baseline_correct = results_by_method["baseline"]["correct"]
        improvements = {}

        for method in self.methods:
            if method != "baseline":
                method_correct = results_by_method[method]["correct"]
                improvements[method] = 1 if (method_correct and not baseline_correct) else 0

        return {
            "methods": results_by_method,
            "baseline_correct": baseline_correct,
            "improvements": improvements,
            "expected_answer": needle_doc.answer
        }

    def _build_context(self, documents: List) -> str:
        """Build context from documents."""
        parts = []
        for doc in documents:
            parts.append(f"Document {doc.doc_id}:\n{doc.content}\n")
        return "\n".join(parts)

    def _create_prompt(self, context: str, question: str) -> str:
        """Create prompt."""
        return f"""Answer the question based ONLY on the provided documents.

{context}

Question: {question}

Answer with ONLY the specific answer (no explanations):"""

    def _check_answer(self, response: str, expected: str) -> bool:
        """Check if answer is correct."""
        response_clean = response.strip().upper()
        expected_clean = expected.strip().upper()
        return expected_clean in response_clean

    def analyze_results(self) -> Dict[str, Any]:
        """Analyze which restructuring methods work best."""
        if not self.results:
            return {}

        # Aggregate by method
        method_accuracies = {method: [] for method in self.methods}

        for result in self.results:
            if not result.metadata.get("success"):
                continue

            methods_data = result.metrics.get("methods", {})
            for method in self.methods:
                if method in methods_data:
                    is_correct = methods_data[method]["correct"]
                    method_accuracies[method].append(1.0 if is_correct else 0.0)

        # Calculate statistics
        method_stats = {}
        for method, accuracies in method_accuracies.items():
            if accuracies:
                method_stats[method] = {
                    "accuracy": np.mean(accuracies),
                    "std": np.std(accuracies),
                    "count": len(accuracies),
                    "improvement_over_baseline": 0.0
                }

        # Calculate improvement over baseline
        baseline_acc = method_stats.get("baseline", {}).get("accuracy", 0)
        for method in method_stats:
            if method != "baseline":
                improvement = method_stats[method]["accuracy"] - baseline_acc
                method_stats[method]["improvement_over_baseline"] = improvement

        analysis = {
            "method_statistics": method_stats,
            "best_method": max(method_stats.items(), key=lambda x: x[1]["accuracy"])[0],
            "summary": self._generate_summary(method_stats)
        }

        self._print_analysis(analysis)
        return analysis

    def _generate_summary(self, method_stats: Dict) -> str:
        """Generate summary."""
        baseline_acc = method_stats.get("baseline", {}).get("accuracy", 0)

        summary = f"""
Context Restructuring Results:
- Baseline accuracy: {baseline_acc:.1%}
"""
        for method in ["relevance", "alternating", "reverse", "random"]:
            if method in method_stats:
                stats = method_stats[method]
                acc = stats["accuracy"]
                improvement = stats["improvement_over_baseline"]
                summary += f"- {method.capitalize()}: {acc:.1%} ({improvement:+.1%})\n"

        return summary.strip()

    def _print_analysis(self, analysis: Dict):
        """Print analysis."""
        print("\n" + "="*60)
        print("CONTEXT RESTRUCTURING ANALYSIS")
        print("="*60)

        print("\nAccuracy by Method:")
        method_stats = analysis["method_statistics"]

        for method in self.methods:
            if method in method_stats:
                stats = method_stats[method]
                acc = stats["accuracy"]
                improvement = stats["improvement_over_baseline"]

                marker = "📍" if method == "baseline" else "  "
                imp_str = f"({improvement:+.1%})" if method != "baseline" else ""

                print(f"{marker} {method:12s}: {acc:6.1%} {imp_str}")

        print(f"\nBest method: {analysis['best_method']}")
        print("\n" + analysis["summary"])
        print("="*60 + "\n")
