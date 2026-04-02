"""
Carbon Outlier Rule — Z-Score-based statistical anomaly detection.

Flags suppliers whose Carbon_Emissions_MT exceeds 3 standard deviations
from their industry mean. This is a standard fraud detection technique
(ISA 240 / BRSR Principle 6).
"""

from __future__ import annotations

from typing import List

import pandas as pd

from src.engines.rules.base import AuditRule
from src.models import AuditException, IssueType, RiskLevel


class CarbonOutlierRule(AuditRule):
    """
    Detect carbon emission outliers using per-industry Z-Score analysis.

    Z-Score = (Value - Mean) / StdDev
    Threshold: Z > 3 (configurable)
    """

    def __init__(self, z_threshold: float = 3.0) -> None:
        self._z_threshold = z_threshold

    @property
    def name(self) -> str:
        return "Carbon Outlier Detection (Z-Score)"

    @property
    def description(self) -> str:
        return (
            f"Flags suppliers with carbon emissions exceeding "
            f"{self._z_threshold} standard deviations from industry mean. "
            f"References BRSR Principle 6 (Environmental Impact)."
        )

    def evaluate(self, df: pd.DataFrame) -> List[AuditException]:
        """
        Vectorized Z-Score computation per industry group.

        Performance note: The original code used iterrows() which is
        O(n) with high constant factor. This uses Pandas group operations
        which leverage NumPy vectorization — ~10-100x faster on large datasets.
        """
        exceptions: List[AuditException] = []

        for industry, group in df.groupby("Industry"):
            mean = group["Carbon_Emissions_MT"].mean()
            std = group["Carbon_Emissions_MT"].std()

            if std == 0:
                continue  # All values identical — no outliers possible

            # Vectorized outlier detection
            outlier_mask = group["Carbon_Emissions_MT"] > (mean + self._z_threshold * std)
            outliers = group[outlier_mask]

            for _, row in outliers.iterrows():
                exceptions.append(AuditException(
                    supplier_id=row["Supplier_ID"],
                    issue=IssueType.CARBON_OUTLIER,
                    details=(
                        f"Emissions ({row['Carbon_Emissions_MT']}) "
                        f"far exceed industry avg ({round(mean, 2)})"
                    ),
                    risk_level=RiskLevel.HIGH,
                ))

        return exceptions
