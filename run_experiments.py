#!/usr/bin/env python3
"""
Main script to run experiments.
"""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.experiments.dead_zone_mapper import DeadZoneMapperExperiment
from src.experiments.context_restructuring_exp import ContextRestructuringExperiment
from src.utils.visualization import ExperimentVisualizer
from config.config import get_experiment_config


def run_dead_zone_mapper(num_trials: int = 10):
    """Run the Dead Zone Mapper experiment."""
    print("\n" + "🔬 "*30)
    print("EXPERIMENT 1: DEAD ZONE MAPPER")
    print("🔬 "*30 + "\n")

    config = get_experiment_config("dead_zone_mapper")

    experiment = DeadZoneMapperExperiment({
        "llm_provider": "openai",
        "llm_model": "gpt-4-turbo-preview",
        "needle_positions": [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95],
        "num_documents": 20,
        "tokens_per_doc": 500
    })

    results = experiment.run(num_trials=num_trials, save=True)

    # Create visualizations
    print("\nGenerating visualizations...")
    visualizer = ExperimentVisualizer()
    results_dir = Path("./results/dead_zone_mapper")

    visualizer.create_summary_report("dead_zone_mapper", results_dir)

    print("\n✅ Dead Zone Mapper experiment complete!\n")
    return results


def run_context_restructuring(num_trials: int = 10):
    """Run the Context Restructuring experiment."""
    print("\n" + "🔬 "*30)
    print("EXPERIMENT 2: CONTEXT RESTRUCTURING")
    print("🔬 "*30 + "\n")

    experiment = ContextRestructuringExperiment({
        "llm_provider": "openai",
        "llm_model": "gpt-4-turbo-preview",
        "num_documents": 20,
        "tokens_per_doc": 500
    })

    results = experiment.run(num_trials=num_trials, save=True)

    # Create visualizations
    print("\nGenerating visualizations...")
    visualizer = ExperimentVisualizer()
    results_dir = Path("./results/context_restructuring")

    visualizer.create_summary_report("context_restructuring", results_dir)

    print("\n✅ Context Restructuring experiment complete!\n")
    return results


def run_all_experiments(num_trials: int = 10):
    """Run all experiments in sequence."""
    print("\n" + "="*80)
    print("RUNNING ALL LOST IN THE MIDDLE EXPERIMENTS")
    print("="*80 + "\n")

    all_results = {}

    # Experiment 1: Dead Zone Mapper
    all_results["dead_zone_mapper"] = run_dead_zone_mapper(num_trials)

    # Experiment 2: Context Restructuring
    all_results["context_restructuring"] = run_context_restructuring(num_trials)

    print("\n" + "="*80)
    print("ALL EXPERIMENTS COMPLETE")
    print("="*80 + "\n")

    print("Results saved to ./results/")
    print("Visualizations saved to ./results/*/visualizations/")

    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Run Lost in the Middle recovery experiments"
    )

    parser.add_argument(
        "experiment",
        choices=["dead_zone", "restructuring", "all"],
        help="Which experiment to run"
    )

    parser.add_argument(
        "--trials",
        type=int,
        default=10,
        help="Number of trials to run (default: 10)"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick test run with minimal trials"
    )

    args = parser.parse_args()

    num_trials = 3 if args.quick else args.trials

    if args.experiment == "dead_zone":
        run_dead_zone_mapper(num_trials)
    elif args.experiment == "restructuring":
        run_context_restructuring(num_trials)
    elif args.experiment == "all":
        run_all_experiments(num_trials)


if __name__ == "__main__":
    main()
