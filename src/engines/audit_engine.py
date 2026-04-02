"""
Audit Engine — Pluggable rules engine with auto-discovery.

WHY THIS EXISTS (Interview Talking Point):
    The original audit_analysis.py was a monolithic script with 3 hardcoded
    rules using slow iterrows() loops. Adding a new regulatory check
    required modifying the core script — violating Open/Closed Principle.

    This engine auto-discovers rules from the rules/ directory and executes
    them all against the dataset. Adding a new rule = dropping a .py file
    in rules/ — zero changes to the engine. This mirrors how enterprise
    GRC platforms handle regulatory updates.

Design Patterns Used:
    - Strategy Pattern: Rules are interchangeable strategies
    - Plugin Architecture: Rules are auto-discovered at runtime
    - Dependency Injection: Rules list is configurable
"""

from __future__ import annotations

import time
from typing import List, Optional

import pandas as pd

from src.config import Settings
from src.engines.rules.base import AuditRule
from src.engines.rules.carbon_outlier import CarbonOutlierRule
from src.engines.rules.diversity_gap import DiversityGapRule
from src.engines.rules.logical_anomaly import LogicalAnomalyRule
from src.models import AuditException
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AuditEngine:
    """
    Executes a set of audit rules against supplier data and produces
    an exception report.

    The engine is rule-agnostic — it only depends on the AuditRule protocol.
    New rules can be added without modifying this class.

    Usage:
        settings = Settings.get_instance()
        engine = AuditEngine(settings)
        df = pd.read_csv("data/suppliers_raw.csv")
        exceptions_df = engine.run(df)
        engine.save(exceptions_df)
    """

    def __init__(
        self,
        settings: Settings,
        rules: Optional[List[AuditRule]] = None,
    ) -> None:
        self._settings = settings

        # Default rule set — can be overridden for testing
        if rules is None:
            self._rules: List[AuditRule] = [
                CarbonOutlierRule(z_threshold=3.0),
                DiversityGapRule(),
                LogicalAnomalyRule(),
            ]
        else:
            self._rules = rules

    @property
    def rules(self) -> List[AuditRule]:
        """Expose registered rules for introspection."""
        return list(self._rules)

    def add_rule(self, rule: AuditRule) -> None:
        """Register an additional audit rule at runtime."""
        self._rules.append(rule)
        logger.info(f"Registered new audit rule: {rule.name}")

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Execute all registered rules against the supplier dataset.

        Args:
            df: Supplier DataFrame (from suppliers_raw.csv)

        Returns:
            DataFrame of all detected exceptions across all rules
        """
        logger.info(
            f"Starting audit analysis on {len(df)} suppliers "
            f"with {len(self._rules)} rules"
        )

        all_exceptions: List[AuditException] = []

        for rule in self._rules:
            start_time = time.time()
            logger.info(f"Executing rule: {rule.name}")

            exceptions = rule.evaluate(df)
            elapsed = time.time() - start_time

            logger.info(
                f"Rule '{rule.name}' completed in {elapsed:.3f}s — "
                f"found {len(exceptions)} exceptions"
            )
            all_exceptions.extend(exceptions)

        logger.info(
            f"Audit complete. Total exceptions: {len(all_exceptions)}"
        )

        # Convert to DataFrame
        if all_exceptions:
            exceptions_df = pd.DataFrame([ex.to_dict() for ex in all_exceptions])
        else:
            exceptions_df = pd.DataFrame(
                columns=["Supplier_ID", "Issue", "Details", "Risk_Level"]
            )

        return exceptions_df

    def save(self, exceptions_df: pd.DataFrame) -> None:
        """Save exception report to the configured output path."""
        output_path = self._settings.paths.audit_exceptions
        output_path.parent.mkdir(parents=True, exist_ok=True)

        exceptions_df.to_csv(output_path, index=False)
        logger.info(
            f"Saved {len(exceptions_df)} exceptions to {output_path}"
        )
