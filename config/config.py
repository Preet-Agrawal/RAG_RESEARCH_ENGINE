"""
Configuration management for the research engine.
"""
import os
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ModelConfig:
    """Configuration for language models."""
    provider: str = "groq"  # groq, openai, anthropic
    model_name: str = "llama-3.1-8b-instant"
    temperature: float = 0.0
    max_tokens: int = 4096
    api_key: Optional[str] = None

    def __post_init__(self):
        if self.api_key is None:
            if self.provider == "groq":
                self.api_key = os.getenv("GROQ_API_KEY")
            elif self.provider == "openai":
                self.api_key = os.getenv("OPENAI_API_KEY")
            elif self.provider == "anthropic":
                self.api_key = os.getenv("ANTHROPIC_API_KEY")


@dataclass
class ExperimentConfig:
    """Configuration for experiments."""
    name: str
    description: str
    num_documents: int = 20
    document_length: int = 500  # tokens per document
    needle_positions: List[float] = field(default_factory=lambda: [0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9])
    num_trials: int = 10
    save_results: bool = True
    results_dir: Path = field(default_factory=lambda: Path("./results"))

    def __post_init__(self):
        self.results_dir = Path(self.results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class DataConfig:
    """Configuration for data generation and loading."""
    data_dir: Path = field(default_factory=lambda: Path("./data"))
    cache_dir: Path = field(default_factory=lambda: Path("./.cache"))

    # Dataset sources
    use_synthetic: bool = True
    use_wikipedia: bool = False
    use_legal_docs: bool = False

    # Synthetic data parameters
    topics: List[str] = field(default_factory=lambda: [
        "artificial intelligence", "climate change", "quantum computing",
        "ancient history", "economics", "biology", "space exploration",
        "philosophy", "literature", "mathematics"
    ])

    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class Config:
    """Master configuration object."""
    model: ModelConfig = field(default_factory=ModelConfig)
    experiment: ExperimentConfig = field(default_factory=lambda: ExperimentConfig(
        name="default",
        description="Default experiment configuration"
    ))
    data: DataConfig = field(default_factory=DataConfig)

    # Global settings
    seed: int = 42
    verbose: bool = True
    log_level: str = "INFO"


def get_default_config() -> Config:
    """Get default configuration."""
    return Config()


def get_experiment_config(experiment_name: str) -> Config:
    """Get configuration for a specific experiment."""
    configs = {
        "dead_zone_mapper": Config(
            experiment=ExperimentConfig(
                name="dead_zone_mapper",
                description="Map attention death zones across context positions",
                num_documents=20,
                needle_positions=[0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95],
                num_trials=20
            )
        ),
        "context_restructuring": Config(
            experiment=ExperimentConfig(
                name="context_restructuring",
                description="Test intelligent context restructuring strategies",
                num_documents=20,
                num_trials=15
            )
        ),
        "chunked_reading": Config(
            experiment=ExperimentConfig(
                name="chunked_reading",
                description="Compare chunked iterative reading vs full context",
                num_documents=20,
                num_trials=15
            )
        ),
        "attention_anchoring": Config(
            experiment=ExperimentConfig(
                name="attention_anchoring",
                description="Test various attention anchoring strategies",
                num_documents=20,
                num_trials=15
            )
        ),
        "query_aware_compression": Config(
            experiment=ExperimentConfig(
                name="query_aware_compression",
                description="Test query-aware document compression and positioning",
                num_documents=20,
                num_trials=15
            )
        )
    }

    return configs.get(experiment_name, get_default_config())
