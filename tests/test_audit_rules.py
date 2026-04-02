"""
Tests for audit rules — each rule tested in isolation with known inputs/outputs.

These tests verify that the rules engine correctly identifies anomalies
without requiring LLM calls or file I/O (pure business logic tests).
"""

import numpy as np
import pandas as pd
import pytest

from src.engines.rules.carbon_outlier import CarbonOutlierRule
from src.engines.rules.diversity_gap import DiversityGapRule
from src.engines.rules.logical_anomaly import LogicalAnomalyRule
from src.models import IssueType, RiskLevel


def _make_supplier_df(overrides: list[dict]) -> pd.DataFrame:
    """Helper: create a minimal supplier DataFrame with overrides."""
    base = {
        "Supplier_ID": "SUP-9999",
        "Company_Name": "TestVendor",
        "Industry": "IT Services",
        "Region": "APAC",
        "Carbon_Emissions_MT": 300.0,
        "Water_Usage_m3": 150.0,
        "Social_Diversity_Score_%": 42.0,
        "Safety_Violations": 0,
        "Last_Audit_Date": "2025-01-01",
        "Compliance_Status": "Certified",
    }
    rows = []
    for i, override in enumerate(overrides):
        row = {**base, **override}
        if "Supplier_ID" not in override:
            row["Supplier_ID"] = f"SUP-{9000 + i}"
        rows.append(row)
    return pd.DataFrame(rows)


class TestCarbonOutlierRule:
    """Tests for Z-Score-based carbon outlier detection."""

    def test_detects_outlier(self):
        """A supplier with extreme emissions should be flagged.

        We need enough tightly-clustered data points so that the standard
        deviation is small and the outlier clearly exceeds mean + 3*std.
        """
        # 20 tightly-clustered normal values + 1 extreme outlier
        normal_rows = [{"Carbon_Emissions_MT": 300.0 + i} for i in range(20)]
        outlier_row = [{"Carbon_Emissions_MT": 30000.0}]  # ~100x average
        df = _make_supplier_df(normal_rows + outlier_row)

        rule = CarbonOutlierRule(z_threshold=3.0)
        exceptions = rule.evaluate(df)
        assert len(exceptions) == 1
        assert exceptions[0].issue == IssueType.CARBON_OUTLIER
        assert exceptions[0].risk_level == RiskLevel.HIGH

    def test_no_false_positives_on_normal_data(self):
        """Normal variation should not trigger outlier detection."""
        df = _make_supplier_df([
            {"Carbon_Emissions_MT": 300.0},
            {"Carbon_Emissions_MT": 310.0},
            {"Carbon_Emissions_MT": 290.0},
            {"Carbon_Emissions_MT": 305.0},
        ])
        rule = CarbonOutlierRule(z_threshold=3.0)
        exceptions = rule.evaluate(df)
        assert len(exceptions) == 0

    def test_respects_industry_grouping(self):
        """Outliers should be computed per industry, not globally."""
        # IT Services: many normal values + 1 outlier
        it_normal = [
            {"Industry": "IT Services", "Carbon_Emissions_MT": 300.0 + i}
            for i in range(15)
        ]
        it_outlier = [
            {"Industry": "IT Services", "Carbon_Emissions_MT": 30000.0,
             "Supplier_ID": "SUP-OUTLIER"}
        ]
        # Energy: values in a high but tight range (no outliers)
        energy_normal = [
            {"Industry": "Energy", "Carbon_Emissions_MT": 50000.0 + i * 100}
            for i in range(10)
        ]
        df = _make_supplier_df(it_normal + it_outlier + energy_normal)

        rule = CarbonOutlierRule(z_threshold=3.0)
        exceptions = rule.evaluate(df)
        # Only the IT Services outlier should be flagged
        flagged_ids = [e.supplier_id for e in exceptions]
        assert "SUP-OUTLIER" in flagged_ids
        # Energy values should NOT be flagged (they're normal for Energy)
        assert all("Energy" not in e.details for e in exceptions)


class TestDiversityGapRule:
    """Tests for null diversity score detection."""

    def test_detects_null_diversity(self):
        """Missing diversity scores should be flagged."""
        df = _make_supplier_df([
            {"Social_Diversity_Score_%": 42.0},
            {"Social_Diversity_Score_%": np.nan},
            {"Social_Diversity_Score_%": None},
        ])
        rule = DiversityGapRule()
        exceptions = rule.evaluate(df)
        assert len(exceptions) == 2
        assert all(e.issue == IssueType.REPORTING_GAP for e in exceptions)
        assert all(e.risk_level == RiskLevel.MEDIUM for e in exceptions)

    def test_no_false_positives(self):
        """Valid diversity scores should not be flagged."""
        df = _make_supplier_df([
            {"Social_Diversity_Score_%": 42.0},
            {"Social_Diversity_Score_%": 0.0},  # Zero is valid, just low
        ])
        rule = DiversityGapRule()
        exceptions = rule.evaluate(df)
        assert len(exceptions) == 0


class TestLogicalAnomalyRule:
    """Tests for physically impossible data detection."""

    def test_detects_zero_water_in_manufacturing(self):
        """Manufacturing + zero water = greenwashing flag."""
        df = _make_supplier_df([
            {"Industry": "Manufacturing", "Water_Usage_m3": 0.0},
        ])
        rule = LogicalAnomalyRule()
        exceptions = rule.evaluate(df)
        assert len(exceptions) == 1
        assert exceptions[0].issue == IssueType.LOGICAL_ANOMALY
        assert exceptions[0].risk_level == RiskLevel.HIGH

    def test_zero_water_ok_for_non_manufacturing(self):
        """Zero water in IT Services is plausible — should not flag."""
        df = _make_supplier_df([
            {"Industry": "IT Services", "Water_Usage_m3": 0.0},
        ])
        rule = LogicalAnomalyRule()
        exceptions = rule.evaluate(df)
        assert len(exceptions) == 0

    def test_non_zero_water_in_manufacturing_ok(self):
        """Normal water usage in manufacturing should not flag."""
        df = _make_supplier_df([
            {"Industry": "Manufacturing", "Water_Usage_m3": 5000.0},
        ])
        rule = LogicalAnomalyRule()
        exceptions = rule.evaluate(df)
        assert len(exceptions) == 0
