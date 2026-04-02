"""
Logical Anomaly Rule — Detects physically impossible data values.

Flags manufacturing suppliers reporting zero water usage, which is
physically impossible and indicates potential greenwashing or sensor failure.
References ISA 240 (Fraud Detection).
"""

from __future__ import annotations

from typing import List

import pandas as pd

from src.engines.rules.base import AuditRule
from src.models import AuditException, IssueType, RiskLevel


class LogicalAnomalyRule(AuditRule):
    """
    Detect logically impossible combinations in supplier data.
    Currently checks: Manufacturing + Zero Water Usage.
    """

    @property
    def name(self) -> str:
        return "Logical Anomaly Detection (Sustainability Paradox)"

    @property
    def description(self) -> str:
        return (
            "Flags physically impossible data values "
            "(e.g., zero water usage in manufacturing). "
            "References ISA 240 (Fraud Detection)."
        )

    def evaluate(self, df: pd.DataFrame) -> List[AuditException]:
        """Vectorized detection of impossible value combinations."""
        exceptions: List[AuditException] = []

        # Manufacturing plants cannot have zero water usage
        anomalies = df[
            (df["Industry"] == "Manufacturing") & (df["Water_Usage_m3"] == 0)
        ]

        for _, row in anomalies.iterrows():
            exceptions.append(AuditException(
                supplier_id=row["Supplier_ID"],
                issue=IssueType.LOGICAL_ANOMALY,
                details=(
                    "Manufacturing reported 0 water usage "
                    "(Potential Greenwashing)."
                ),
                risk_level=RiskLevel.HIGH,
            ))

        return exceptions
