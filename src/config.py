"""
Centralized Configuration — Singleton Pattern + 12-Factor App Methodology.

WHY THIS EXISTS (Interview Talking Point):
    The original codebase had hardcoded paths (e.g., 'E:/analytics/...')
    and API keys embedded directly in notebook cells. This violates the
    12-Factor App methodology (https://12factor.net/config), where
    config should be stored in the environment, not in code.

    This module implements a thread-safe Singleton pattern so that
    configuration is loaded exactly once and shared across all modules.
    All values are read from environment variables (with .env file support),
    making the system deployable across dev/staging/prod without code changes.

Design Patterns Used:
    - Singleton: Ensures one global config instance
    - 12-Factor Config: Environment-variable-driven settings
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Dict, Optional

# python-dotenv is used to load .env files for local development.
# In production, environment variables are set by the deployment platform.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars can be set directly


def _resolve_project_root() -> Path:
    """Walk up from this file to find the project root (where .env.example lives)."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".env.example").exists() or (current / "README.md").exists():
            return current
        current = current.parent
    # Fallback: parent of /src
    return Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class PathConfig:
    """Immutable path configuration — all paths are absolute and resolved at startup."""
    project_root: Path
    data_dir: Path
    plots_dir: Path
    reports_dir: Path

    # Derived artifact paths
    @property
    def suppliers_raw(self) -> Path:
        return self.data_dir / "suppliers_raw.csv"

    @property
    def audit_exceptions(self) -> Path:
        return self.data_dir / "audit_exceptions.csv"

    @property
    def final_audit_memos(self) -> Path:
        return self.data_dir / "final_audit_memos.csv"

    @property
    def dashboard_master_data(self) -> Path:
        return self.data_dir / "dashboard_master_data.csv"


@dataclass(frozen=True)
class LLMConfig:
    """LLM provider configuration — separated for easy provider swaps."""
    api_key: str
    model: str
    temperature: float
    system_prompt: str
    rate_limit_delay: float
    max_retries: int
    max_concurrent_requests: int


@dataclass(frozen=True)
class DataGenConfig:
    """Data generation configuration — controls synthetic data properties."""
    num_suppliers: int
    random_seed: int
    # Industry-specific baselines: maps industry name -> (carbon, water, diversity) ranges
    industry_baselines: Dict[str, Dict[str, tuple]] = field(default_factory=lambda: {
        "Manufacturing": {"carbon": (5000, 15000), "water": (2000, 8000), "diversity": (10, 25)},
        "IT Services":   {"carbon": (100, 500),   "water": (50, 200),    "diversity": (35, 50)},
        "Energy":        {"carbon": (40000, 100000), "water": (5000, 20000), "diversity": (5, 15)},
        "Consumer Goods":{"carbon": (1000, 5000),  "water": (1000, 4000), "diversity": (20, 40)},
        "Healthcare":    {"carbon": (500, 2000),   "water": (500, 1500),  "diversity": (30, 45)},
    })
    # Anomaly injection probabilities
    carbon_spike_probability: float = 0.05
    carbon_spike_multiplier: float = 10.0
    diversity_gap_probability: float = 0.08
    zero_water_probability: float = 0.03


@dataclass(frozen=True)
class LogConfig:
    """Logging configuration."""
    level: str
    format: str  # "json" or "text"


class Settings:
    """
    Application-wide settings — Singleton Pattern.

    Usage:
        settings = Settings.get_instance()
        print(settings.paths.data_dir)
        print(settings.llm.model)
    """

    _instance: ClassVar[Optional[Settings]] = None

    def __init__(self) -> None:
        root = _resolve_project_root()

        self.paths = PathConfig(
            project_root=root,
            data_dir=root / os.getenv("DATA_DIR", "./data"),
            plots_dir=root / os.getenv("PLOTS_DIR", "./plots"),
            reports_dir=root / os.getenv("REPORTS_DIR", "./reports"),
        )

        self.llm = LLMConfig(
            api_key=os.getenv("GROQ_API_KEY", ""),
            model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
            system_prompt=os.getenv(
                "LLM_SYSTEM_PROMPT",
                "You are a rigid, no-nonsense ESG Auditor at EY. "
                "Output ONLY the requested audit memo format."
            ),
            rate_limit_delay=float(os.getenv("RATE_LIMIT_DELAY", "1.5")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            max_concurrent_requests=int(os.getenv("MAX_CONCURRENT_REQUESTS", "5")),
        )

        self.datagen = DataGenConfig(
            num_suppliers=int(os.getenv("NUM_SUPPLIERS", "1000")),
            random_seed=int(os.getenv("RANDOM_SEED", "42")),
        )

        self.log = LogConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            format=os.getenv("LOG_FORMAT", "json"),
        )

    @classmethod
    def get_instance(cls) -> Settings:
        """Thread-safe-ish singleton accessor (sufficient for single-process CLI tools)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton — useful for testing with different env configs."""
        cls._instance = None
