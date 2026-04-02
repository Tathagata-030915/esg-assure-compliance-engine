"""
Diversity Reporting Gap Rule — Null-value detection for mandatory disclosures.

Flags suppliers with missing Social_Diversity_Score_% values,
which violates SEBI BRSR Core mandatory disclosure requirements.
"""

from __future__ import annotations

from typing import List

import pandas as pd

from src.engines.rules.base import AuditRule
from src.models import AuditException, IssueType, RiskLevel


class DiversityGapRule(AuditRule):
    """
    Detect missing/null values in mandatory social diversity reporting fields.
    """

    @property
    def name(self) -> str:
        return "Diversity Reporting Gap Detection"

    @property
    def description(self) -> str:
        return (
            "Flags suppliers with null/missing diversity scores. "
            "References SEBI BRSR Core - Mandatory Disclosure."
        )

    def evaluate(self, df: pd.DataFrame) -> List[AuditException]:
        """Vectorized null detection on diversity score column."""
        exceptions: List[AuditException] = []

        missing = df[df["Social_Diversity_Score_%"].isna()]

        for _, row in missing.iterrows():
            exceptions.append(AuditException(
                supplier_id=row["Supplier_ID"],
                issue=IssueType.REPORTING_GAP,
                details="Diversity score missing or null.",
                risk_level=RiskLevel.MEDIUM,
            ))

        return exceptions
