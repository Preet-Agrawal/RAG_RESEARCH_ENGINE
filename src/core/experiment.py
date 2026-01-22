"""
Base experiment class and framework.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import json
import time
from pathlib import Path
import pandas as pd
from datetime import datetime


@dataclass
class ExperimentResult:
    """Single experiment trial result."""
    experiment_name: str
    trial_id: int
    config: Dict[str, Any]
    metrics: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: str
    duration: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class Experiment(ABC):
    """Base class for all experiments."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.results: List[ExperimentResult] = []

    @abstractmethod
    def setup(self):
        """Setup experiment (data generation, initialization, etc.)."""
        pass

    @abstractmethod
    def run_trial(self, trial_id: int) -> Dict[str, Any]:
        """
        Run a single trial of the experiment.

        Args:
            trial_id: Unique identifier for this trial

        Returns:
            Dictionary containing trial metrics
        """
        pass

    @abstractmethod
    def analyze_results(self) -> Dict[str, Any]:
        """
        Analyze aggregated results from all trials.

        Returns:
            Dictionary containing analysis results and statistics
        """
        pass

    def run(self, num_trials: int = 10, save: bool = True) -> List[ExperimentResult]:
        """
        Run the full experiment with multiple trials.

        Args:
            num_trials: Number of trials to run
            save: Whether to save results to disk

        Returns:
            List of ExperimentResult objects
        """
        print(f"\n{'='*60}")
        print(f"Running Experiment: {self.name}")
        print(f"Number of trials: {num_trials}")
        print(f"{'='*60}\n")

        self.setup()

        for trial_id in range(num_trials):
            print(f"Running trial {trial_id + 1}/{num_trials}...", end=" ")
            start_time = time.time()

            try:
                metrics = self.run_trial(trial_id)
                duration = time.time() - start_time

                result = ExperimentResult(
                    experiment_name=self.name,
                    trial_id=trial_id,
                    config=self.config,
                    metrics=metrics,
                    metadata={"success": True},
                    timestamp=datetime.now().isoformat(),
                    duration=duration
                )

                self.results.append(result)
                print(f"✓ ({duration:.2f}s)")

            except Exception as e:
                duration = time.time() - start_time
                print(f"✗ Error: {str(e)}")

                result = ExperimentResult(
                    experiment_name=self.name,
                    trial_id=trial_id,
                    config=self.config,
                    metrics={},
                    metadata={"success": False, "error": str(e)},
                    timestamp=datetime.now().isoformat(),
                    duration=duration
                )
                self.results.append(result)

        print(f"\n{'='*60}")
        print(f"Experiment completed: {len([r for r in self.results if r.metadata.get('success')])}/{num_trials} successful")
        print(f"{'='*60}\n")

        if save:
            self.save_results()

        # Run analysis
        print("Analyzing results...")
        analysis = self.analyze_results()

        return self.results

    def save_results(self, output_dir: Optional[Path] = None):
        """Save results to disk."""
        if output_dir is None:
            output_dir = Path("./results") / self.name

        output_dir.mkdir(parents=True, exist_ok=True)

        # Save individual results as JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = output_dir / f"results_{timestamp}.json"

        with open(json_path, 'w') as f:
            json.dump([r.to_dict() for r in self.results], f, indent=2)

        # Save as CSV for easy analysis
        csv_path = output_dir / f"results_{timestamp}.csv"
        df = self.results_to_dataframe()
        df.to_csv(csv_path, index=False)

        print(f"Results saved to: {output_dir}")

    def results_to_dataframe(self) -> pd.DataFrame:
        """Convert results to pandas DataFrame."""
        records = []
        for result in self.results:
            record = {
                "experiment_name": result.experiment_name,
                "trial_id": result.trial_id,
                "timestamp": result.timestamp,
                "duration": result.duration,
                "success": result.metadata.get("success", False)
            }

            # Add all metrics as columns
            for key, value in result.metrics.items():
                record[f"metric_{key}"] = value

            # Add config parameters
            for key, value in result.config.items():
                record[f"config_{key}"] = value

            records.append(record)

        return pd.DataFrame(records)

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Get summary statistics from results."""
        df = self.results_to_dataframe()

        # Get all metric columns
        metric_cols = [col for col in df.columns if col.startswith("metric_")]

        summary = {
            "total_trials": len(self.results),
            "successful_trials": len([r for r in self.results if r.metadata.get("success")]),
            "average_duration": df["duration"].mean(),
            "metrics": {}
        }

        for col in metric_cols:
            metric_name = col.replace("metric_", "")
            summary["metrics"][metric_name] = {
                "mean": df[col].mean(),
                "std": df[col].std(),
                "min": df[col].min(),
                "max": df[col].max(),
                "median": df[col].median()
            }

        return summary
