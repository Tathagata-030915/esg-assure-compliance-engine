"""
Supplier Data Generator — Strategy Pattern for Anomaly Injection.

WHY THIS EXISTS (Interview Talking Point):
    The original data_generation.py was a single procedural script with:
    - Hardcoded output path ('E:/analytics/...')
    - Anomaly injection logic mixed with data generation
    - No type hints, no error handling, no logging

    This refactored version uses the Strategy Pattern: each anomaly type
    (Carbon Spike, Diversity Gap, Zero Water) is a separate class implementing
    the AnomalyStrategy protocol. This makes anomalies:
    - Independently testable
    - Composable (add/remove anomalies without touching generator code)
    - Configurable (probabilities from config, not hardcoded)

Design Patterns Used:
    - Strategy Pattern: AnomalyStrategy protocol + concrete implementations
    - Factory Method: SupplierGenerator.create_supplier()
    - Dependency Injection: Config injected, not imported globally
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Protocol

import numpy as np
import pandas as pd

from src.config import Settings
from src.models import Supplier
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─── Anomaly Strategy Protocol ───────────────────────────────────────────────

class AnomalyStrategy(ABC):
    """
    Protocol for anomaly injection strategies.
    Each strategy decides whether to mutate a supplier record and how.
    """

    @abstractmethod
    def apply(self, supplier: Supplier, industry: str) -> Supplier:
        """
        Potentially mutate a supplier record to inject an anomaly.
        Returns the (possibly modified) supplier.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for logging."""
        ...


# ─── Concrete Anomaly Strategies ─────────────────────────────────────────────

class CarbonSpikeAnomaly(AnomalyStrategy):
    """
    Red Flag 1: Carbon Spike.
    A percentage of suppliers have emissions multiplied by a large factor,
    simulating unreported industrial spills or fraudulent baseline reporting.
    """

    def __init__(self, probability: float = 0.05, multiplier: float = 10.0) -> None:
        self._probability = probability
        self._multiplier = multiplier

    @property
    def name(self) -> str:
        return "Carbon Spike"

    def apply(self, supplier: Supplier, industry: str) -> Supplier:
        if random.random() < self._probability:
            supplier.carbon_emissions_mt *= self._multiplier
            logger.debug(
                f"Injected Carbon Spike for {supplier.supplier_id}: "
                f"emissions -> {supplier.carbon_emissions_mt:.2f}"
            )
        return supplier


class DiversityGapAnomaly(AnomalyStrategy):
    """
    Red Flag 2: Diversity Reporting Gap.
    Some suppliers have null/missing diversity scores, violating mandatory
    SEBI BRSR disclosure requirements.
    """

    def __init__(self, probability: float = 0.08) -> None:
        self._probability = probability

    @property
    def name(self) -> str:
        return "Diversity Gap"

    def apply(self, supplier: Supplier, industry: str) -> Supplier:
        if random.random() < self._probability:
            supplier.social_diversity_score = None
            logger.debug(
                f"Injected Diversity Gap for {supplier.supplier_id}: "
                f"diversity score -> None"
            )
        return supplier


class ZeroWaterAnomaly(AnomalyStrategy):
    """
    Red Flag 3: Sustainability Paradox.
    Manufacturing plants reporting zero water usage — physically impossible.
    Indicates potential greenwashing or sensor failure.
    """

    def __init__(self, probability: float = 0.03) -> None:
        self._probability = probability

    @property
    def name(self) -> str:
        return "Zero Water"

    def apply(self, supplier: Supplier, industry: str) -> Supplier:
        if industry == "Manufacturing" and random.random() < self._probability:
            supplier.water_usage_m3 = 0.0
            logger.debug(
                f"Injected Zero Water for {supplier.supplier_id}: "
                f"water usage -> 0.0"
            )
        return supplier


# ─── Supplier Generator ─────────────────────────────────────────────────────

class SupplierGenerator:
    """
    Generates synthetic supplier data with configurable anomaly injection.

    Usage:
        settings = Settings.get_instance()
        generator = SupplierGenerator(settings)
        df = generator.generate()
        generator.save(df)
    """

    def __init__(
        self,
        settings: Settings,
        anomaly_strategies: Optional[List[AnomalyStrategy]] = None,
    ) -> None:
        self._settings = settings
        self._config = settings.datagen
        self._industries = self._config.industry_baselines

        # Default anomaly strategies from config
        if anomaly_strategies is None:
            self._strategies = [
                CarbonSpikeAnomaly(
                    probability=self._config.carbon_spike_probability,
                    multiplier=self._config.carbon_spike_multiplier,
                ),
                DiversityGapAnomaly(
                    probability=self._config.diversity_gap_probability,
                ),
                ZeroWaterAnomaly(
                    probability=self._config.zero_water_probability,
                ),
            ]
        else:
            self._strategies = anomaly_strategies

    def _create_supplier(self, index: int) -> Supplier:
        """Factory method: creates a single supplier with baseline data."""
        industry = random.choice(list(self._industries.keys()))
        baselines = self._industries[industry]

        supplier = Supplier(
            supplier_id=f"SUP-{1000 + index}",
            company_name=f"Vendor_{index}",
            industry=industry,
            region=random.choice(["APAC", "EMEA", "NA", "LATAM"]),
            carbon_emissions_mt=np.random.uniform(*baselines["carbon"]),
            water_usage_m3=np.random.uniform(*baselines["water"]),
            social_diversity_score=np.random.uniform(*baselines["diversity"]),
            safety_violations=int(np.random.poisson(lam=1.2)),
            last_audit_date=(
                datetime.now() - timedelta(days=random.randint(0, 365))
            ).strftime("%Y-%m-%d"),
            compliance_status="Certified",
        )

        # Apply anomaly strategies in sequence
        for strategy in self._strategies:
            supplier = strategy.apply(supplier, industry)

        return supplier

    def generate(self) -> pd.DataFrame:
        """
        Generate the full synthetic supplier dataset.

        Returns:
            DataFrame with all supplier records, anomalies injected.
        """
        np.random.seed(self._config.random_seed)
        random.seed(self._config.random_seed)

        logger.info(
            f"Generating {self._config.num_suppliers} suppliers "
            f"with seed={self._config.random_seed}"
        )
        logger.info(
            f"Active anomaly strategies: "
            f"{[s.name for s in self._strategies]}"
        )

        suppliers = [
            self._create_supplier(i).to_dict()
            for i in range(self._config.num_suppliers)
        ]

        df = pd.DataFrame(suppliers)

        # Summary stats
        carbon_outliers = (df["Carbon_Emissions_MT"] > 50000).sum()
        diversity_gaps = df["Social_Diversity_Score_%"].isna().sum()
        zero_water = (
            (df["Industry"] == "Manufacturing") & (df["Water_Usage_m3"] == 0)
        ).sum()

        logger.info(
            f"Generation complete: {len(df)} rows, "
            f"{carbon_outliers} carbon outliers, "
            f"{diversity_gaps} diversity gaps, "
            f"{zero_water} zero-water anomalies"
        )

        return df

    def save(self, df: pd.DataFrame) -> None:
        """Save generated data to the configured output path."""
        output_path = self._settings.paths.suppliers_raw

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        df.to_csv(output_path, index=False)
        logger.info(f"Saved supplier data to {output_path}")
