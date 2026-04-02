"""
Tests for domain models — validates data contracts between pipeline stages.
"""

import pytest
from src.models import (
    AuditException,
    AuditMemo,
    IssueType,
    RiskLevel,
    Supplier,
    RegulatoryContext,
    REGULATORY_CONTEXT_MAP,
)


class TestSupplierModel:
    """Tests for the Supplier domain model."""

    def test_supplier_creation(self):
        """A supplier should be creatable with all required fields."""
        s = Supplier(
            supplier_id="SUP-1000",
            company_name="TestVendor",
            industry="IT Services",
            region="APAC",
            carbon_emissions_mt=250.0,
            water_usage_m3=150.0,
            social_diversity_score=42.5,
            safety_violations=1,
            last_audit_date="2025-01-15",
        )
        assert s.supplier_id == "SUP-1000"
        assert s.carbon_emissions_mt == 250.0

    def test_supplier_to_dict_rounds_values(self):
        """to_dict() should round numeric fields to 2 decimal places."""
        s = Supplier(
            supplier_id="SUP-1001",
            company_name="TestVendor",
            industry="Energy",
            region="EMEA",
            carbon_emissions_mt=12345.6789,
            water_usage_m3=9876.5432,
            social_diversity_score=33.333,
            safety_violations=0,
            last_audit_date="2025-06-01",
        )
        d = s.to_dict()
        assert d["Carbon_Emissions_MT"] == 12345.68
        assert d["Water_Usage_m3"] == 9876.54
        assert d["Social_Diversity_Score_%"] == 33.33

    def test_supplier_null_diversity_score(self):
        """Null diversity scores should serialize as None (for CSV NaN)."""
        s = Supplier(
            supplier_id="SUP-1002",
            company_name="Vendor_2",
            industry="Manufacturing",
            region="NA",
            carbon_emissions_mt=8000.0,
            water_usage_m3=5000.0,
            social_diversity_score=None,
            safety_violations=2,
            last_audit_date="2025-03-20",
        )
        d = s.to_dict()
        assert d["Social_Diversity_Score_%"] is None


class TestEnums:
    """Tests for domain enumerations."""

    def test_risk_level_values(self):
        """RiskLevel should have exactly 3 values."""
        assert len(RiskLevel) == 3
        assert RiskLevel.HIGH.value == "High"
        assert RiskLevel.MEDIUM.value == "Medium"
        assert RiskLevel.LOW.value == "Low/Compliant"

    def test_issue_type_values(self):
        """IssueType should have exactly 3 values."""
        assert len(IssueType) == 3
        assert IssueType.CARBON_OUTLIER.value == "Carbon Outlier"

    def test_risk_level_str_serialization(self):
        """Enums should serialize cleanly to strings for CSV output."""
        assert str(RiskLevel.HIGH) == "High"
        assert str(IssueType.REPORTING_GAP) == "Reporting Gap"

    def test_issue_type_from_string(self):
        """Should be constructable from string values (for CSV ingestion)."""
        assert IssueType("Carbon Outlier") == IssueType.CARBON_OUTLIER
        assert IssueType("Reporting Gap") == IssueType.REPORTING_GAP


class TestAuditException:
    """Tests for AuditException model."""

    def test_exception_to_dict(self):
        """to_dict() should produce correct CSV-compatible output."""
        ex = AuditException(
            supplier_id="SUP-1064",
            issue=IssueType.CARBON_OUTLIER,
            details="Emissions (2735.41) far exceed industry avg (460.8)",
            risk_level=RiskLevel.HIGH,
        )
        d = ex.to_dict()
        assert d["Supplier_ID"] == "SUP-1064"
        assert d["Issue"] == "Carbon Outlier"
        assert d["Risk_Level"] == "High"


class TestRegulatoryContextMap:
    """Tests for the regulatory knowledge base."""

    def test_all_issue_types_have_context(self):
        """Every IssueType must have a corresponding regulatory context."""
        for issue_type in IssueType:
            assert issue_type in REGULATORY_CONTEXT_MAP, (
                f"Missing regulatory context for {issue_type}"
            )

    def test_context_fields_non_empty(self):
        """All regulatory context fields should be non-empty strings."""
        for issue_type, ctx in REGULATORY_CONTEXT_MAP.items():
            assert ctx.regulation, f"Empty regulation for {issue_type}"
            assert ctx.requirement, f"Empty requirement for {issue_type}"
            assert ctx.recommended_action, f"Empty action for {issue_type}"
