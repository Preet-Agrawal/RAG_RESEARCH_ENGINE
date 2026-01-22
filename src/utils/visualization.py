"""
Visualization utilities for experiment results.
"""
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
import json


class ExperimentVisualizer:
    """Create visualizations for experiment results."""

    def __init__(self, style: str = "seaborn-v0_8-darkgrid"):
        sns.set_theme()
        self.colors = sns.color_palette("husl", 8)

    def plot_dead_zone_map(self, results: List[Dict], save_path: Path = None):
        """
        Plot the attention death zone map (U-curve).

        Args:
            results: List of experiment results
            save_path: Path to save figure
        """
        # Extract position accuracies
        position_data = {}

        for result in results:
            if not result.get("metadata", {}).get("success"):
                continue

            positions = result.get("metrics", {}).get("positions", {})
            for pos_key, pos_result in positions.items():
                position = float(pos_key.replace("pos_", ""))
                if position not in position_data:
                    position_data[position] = []
                position_data[position].append(1.0 if pos_result["correct"] else 0.0)

        # Calculate means and stds
        positions = sorted(position_data.keys())
        accuracies = [np.mean(position_data[pos]) for pos in positions]
        stds = [np.std(position_data[pos]) for pos in positions]

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 7))

        # Plot with error bars
        ax.plot(positions, accuracies, 'o-', linewidth=2, markersize=8,
                color=self.colors[0], label='Accuracy')
        ax.fill_between(positions,
                        [acc - std for acc, std in zip(accuracies, stds)],
                        [acc + std for acc, std in zip(accuracies, stds)],
                        alpha=0.3, color=self.colors[0])

        # Highlight dead zone
        mid_start = 0.3
        mid_end = 0.7
        ax.axvspan(mid_start, mid_end, alpha=0.2, color='red', label='Dead Zone')

        # Formatting
        ax.set_xlabel('Position in Context', fontsize=12, fontweight='bold')
        ax.set_ylabel('Retrieval Accuracy', fontsize=12, fontweight='bold')
        ax.set_title('Lost in the Middle: Attention Death Zone Map',
                    fontsize=14, fontweight='bold')
        ax.set_ylim(0, 1.05)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0%}'))
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)

        # Add annotations
        min_acc_idx = np.argmin(accuracies)
        ax.annotate(f'Worst: {accuracies[min_acc_idx]:.1%}',
                   xy=(positions[min_acc_idx], accuracies[min_acc_idx]),
                   xytext=(positions[min_acc_idx], accuracies[min_acc_idx] - 0.15),
                   arrowprops=dict(arrowstyle='->', color='red', lw=2),
                   fontsize=10, ha='center', color='red', fontweight='bold')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")

        return fig

    def plot_strategy_comparison(self, results: Dict[str, List[Dict]],
                                 save_path: Path = None):
        """
        Compare different recovery strategies.

        Args:
            results: Dict mapping strategy name to results
            save_path: Path to save figure
        """
        # Calculate accuracies for each strategy
        strategy_data = {}

        for strategy_name, strategy_results in results.items():
            accuracies = []
            for result in strategy_results:
                if result.get("metadata", {}).get("success"):
                    acc = result.get("metrics", {}).get("accuracy", 0)
                    accuracies.append(acc)

            if accuracies:
                strategy_data[strategy_name] = {
                    "mean": np.mean(accuracies),
                    "std": np.std(accuracies),
                    "values": accuracies
                }

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 7))

        strategies = list(strategy_data.keys())
        means = [strategy_data[s]["mean"] for s in strategies]
        stds = [strategy_data[s]["std"] for s in strategies]

        x = np.arange(len(strategies))
        bars = ax.bar(x, means, yerr=stds, capsize=5, alpha=0.8,
                     color=self.colors[:len(strategies)])

        # Formatting
        ax.set_xlabel('Strategy', fontsize=12, fontweight='bold')
        ax.set_ylabel('Accuracy', fontsize=12, fontweight='bold')
        ax.set_title('Recovery Strategy Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(strategies, rotation=45, ha='right')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
        ax.set_ylim(0, 1.05)
        ax.grid(True, axis='y', alpha=0.3)

        # Add value labels on bars
        for i, (mean, std) in enumerate(zip(means, stds)):
            ax.text(i, mean + std + 0.02, f'{mean:.1%}',
                   ha='center', va='bottom', fontweight='bold')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")

        return fig

    def plot_position_heatmap(self, results: List[Dict], save_path: Path = None):
        """
        Create heatmap showing accuracy across trials and positions.

        Args:
            results: List of experiment results
            save_path: Path to save figure
        """
        # Build matrix: trials x positions
        positions = None
        accuracy_matrix = []

        for result in results:
            if not result.get("metadata", {}).get("success"):
                continue

            positions_data = result.get("metrics", {}).get("positions", {})

            if positions is None:
                positions = sorted([float(k.replace("pos_", ""))
                                  for k in positions_data.keys()])

            trial_accuracies = []
            for pos in positions:
                key = f"pos_{pos:.2f}"
                is_correct = positions_data.get(key, {}).get("correct", False)
                trial_accuracies.append(1.0 if is_correct else 0.0)

            accuracy_matrix.append(trial_accuracies)

        accuracy_matrix = np.array(accuracy_matrix)

        # Create heatmap
        fig, ax = plt.subplots(figsize=(14, 8))

        sns.heatmap(accuracy_matrix, annot=False, cmap="RdYlGn",
                   cbar_kws={'label': 'Correct (1) / Incorrect (0)'},
                   xticklabels=[f'{p:.0%}' for p in positions],
                   yticklabels=[f'Trial {i+1}' for i in range(len(accuracy_matrix))],
                   ax=ax, vmin=0, vmax=1)

        ax.set_xlabel('Position in Context', fontsize=12, fontweight='bold')
        ax.set_ylabel('Trial', fontsize=12, fontweight='bold')
        ax.set_title('Accuracy Heatmap: Trials vs. Positions',
                    fontsize=14, fontweight='bold')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")

        return fig

    def plot_method_comparison(self, results: List[Dict], save_path: Path = None):
        """
        Compare methods within an experiment (e.g., restructuring methods).

        Args:
            results: List of experiment results with 'methods' key
            save_path: Path to save figure
        """
        # Aggregate by method
        method_data = {}

        for result in results:
            if not result.get("metadata", {}).get("success"):
                continue

            methods = result.get("metrics", {}).get("methods", {})
            for method_name, method_result in methods.items():
                if method_name not in method_data:
                    method_data[method_name] = []

                is_correct = method_result.get("correct", False)
                method_data[method_name].append(1.0 if is_correct else 0.0)

        # Calculate statistics
        method_stats = {}
        for method, accuracies in method_data.items():
            method_stats[method] = {
                "mean": np.mean(accuracies),
                "std": np.std(accuracies)
            }

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 7))

        methods = list(method_stats.keys())
        means = [method_stats[m]["mean"] for m in methods]
        stds = [method_stats[m]["std"] for m in methods]

        x = np.arange(len(methods))
        bars = ax.bar(x, means, yerr=stds, capsize=5, alpha=0.8,
                     color=self.colors[:len(methods)])

        # Highlight baseline
        if "baseline" in methods:
            baseline_idx = methods.index("baseline")
            bars[baseline_idx].set_edgecolor('black')
            bars[baseline_idx].set_linewidth(2)

        ax.set_xlabel('Method', fontsize=12, fontweight='bold')
        ax.set_ylabel('Accuracy', fontsize=12, fontweight='bold')
        ax.set_title('Method Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(methods, rotation=45, ha='right')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
        ax.set_ylim(0, 1.05)
        ax.grid(True, axis='y', alpha=0.3)

        # Add value labels
        for i, (mean, std) in enumerate(zip(means, stds)):
            ax.text(i, mean + std + 0.02, f'{mean:.1%}',
                   ha='center', va='bottom', fontweight='bold', fontsize=9)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")

        return fig

    def create_summary_report(self, experiment_name: str, results_dir: Path):
        """
        Create a comprehensive summary report with all visualizations.

        Args:
            experiment_name: Name of experiment
            results_dir: Directory containing results
        """
        # Load results
        results_files = list(results_dir.glob("results_*.json"))

        if not results_files:
            print(f"No results found in {results_dir}")
            return

        latest_results = max(results_files, key=lambda p: p.stat().st_mtime)

        with open(latest_results, 'r') as f:
            results = json.load(f)

        print(f"Loaded {len(results)} results from {latest_results}")

        # Create visualizations based on experiment type
        output_dir = results_dir / "visualizations"
        output_dir.mkdir(exist_ok=True)

        if experiment_name == "dead_zone_mapper":
            self.plot_dead_zone_map(results, output_dir / "dead_zone_map.png")
            self.plot_position_heatmap(results, output_dir / "position_heatmap.png")

        elif "restructuring" in experiment_name or "anchoring" in experiment_name:
            self.plot_method_comparison(results, output_dir / "method_comparison.png")

        print(f"Visualizations saved to {output_dir}")
