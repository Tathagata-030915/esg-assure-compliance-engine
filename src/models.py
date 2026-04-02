"""
Domain Models — Typed Data Structures for the ESG-Assure Pipeline.

WHY THIS EXISTS (Interview Talking Point):
    The original codebase used raw dictionaries and untyped DataFrames
    throughout. This leads to runtime KeyError crashes, no IDE autocompletion,
    and makes it impossible for new engineers to understand the data contracts
    between pipeline stages.

    These dataclasses serve as the "lingua franca" of the system:
    every pipeline stage consumes and produces typed, validated objects.
    This is essential in audit/compliance software where data integrity
    is non-negotiable.

Design Patterns Used:
    - Value Objects: Immutable dataclasses representing domain entities
    - Enum Pattern: Risk levels and issue types have closed, validated sets
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


# ─── Enums ────────────────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    """
    Risk classification for audit exceptions.
    Inherits from str so it serializes cleanly to CSV/JSON.
    """
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low/Compliant"

    def __str__(self) -> str:
        return self.value


class IssueType(str, Enum):
    """
    Categories of audit exceptions detected by the rules engine.
    Maps 1:1 to regulatory context entries — this coupling is intentional
    to ensure every detected issue has a grounded regulatory reference.
    """
    CARBON_OUTLIER = "Carbon Outlier"
    REPORTING_GAP = "Reporting Gap"
    LOGICAL_ANOMALY = "Logical Anomaly"

    def __str__(self) -> str:
        return self.value


class Industry(str, Enum):
    """Valid industry classifications for suppliers."""
    MANUFACTURING = "Manufacturing"
    IT_SERVICES = "IT Services"
    ENERGY = "Energy"
    CONSUMER_GOODS = "Consumer Goods"
    HEALTHCARE = "Healthcare"

    def __str__(self) -> str:
        return self.value


class Region(str, Enum):
    """Geographic regions for supplier classification."""
    APAC = "APAC"
    EMEA = "EMEA"
    NA = "NA"
    LATAM = "LATAM"

    def __str__(self) -> str:
        return self.value


# ─── Domain Models ────────────────────────────────────────────────────────────

@dataclass
class Supplier:
    """
    Represents a single supplier record in the raw dataset.
    This is the input to the audit engine.
    """
    supplier_id: str
    company_name: str
    industry: str
    region: str
    carbon_emissions_mt: float
    water_usage_m3: float
    social_diversity_score: Optional[float]  # Can be null (reporting gap)
    safety_violations: int
    last_audit_date: str
    compliance_status: str = "Certified"

    def to_dict(self) -> dict:
        """Convert to dictionary for DataFrame construction."""
        return {
            "Supplier_ID": self.supplier_id,
            "Company_Name": self.company_name,
            "Industry": self.industry,
            "Region": self.region,
            "Carbon_Emissions_MT": round(self.carbon_emissions_mt, 2),
            "Water_Usage_m3": round(self.water_usage_m3, 2),
            "Social_Diversity_Score_%": (
                round(self.social_diversity_score, 2)
                if self.social_diversity_score is not None
                else None
            ),
            "Safety_Violations": self.safety_violations,
            "Last_Audit_Date": self.last_audit_date,
            "Compliance_Status": self.compliance_status,
        }


@dataclass
class AuditException:
    """
    Represents a flagged anomaly detected by the audit rules engine.
    This is the output of the audit engine and input to the GenAI auditor.
    """
    supplier_id: str
    issue: IssueType
    details: str
    risk_level: RiskLevel

    def to_dict(self) -> dict:
        return {
            "Supplier_ID": self.supplier_id,
            "Issue": str(self.issue),
            "Details": self.details,
            "Risk_Level": str(self.risk_level),
        }


@dataclass
class RegulatoryContext:
    """
    Regulatory grounding for a specific issue type.
    In a production RAG system, this would come from a vector database.
    Here it serves as a lightweight, deterministic substitute.
    """
    issue_type: IssueType
    regulation: str
    requirement: str
    recommended_action: str


@dataclass
class AuditMemo:
    """
    AI-generated audit observation memo.
    This is the final output that goes into the Power BI dashboard.
    """
    supplier_id: str
    industry: str
    risk_level: str
    ai_audit_memo: str

    def to_dict(self) -> dict:
        return {
            "Supplier_ID": self.supplier_id,
            "Industry": self.industry,
            "Risk_Level": self.risk_level,
            "AI_Audit_Memo": self.ai_audit_memo,
        }


# ─── Regulatory Knowledge Base ───────────────────────────────────────────────

# This is the "Regulatory Brain" — hardcoded for determinism.
# In production, this would be a RAG pipeline querying a vector DB.
REGULATORY_CONTEXT_MAP: dict[IssueType, RegulatoryContext] = {
    IssueType.CARBON_OUTLIER: RegulatoryContext(
        issue_type=IssueType.CARBON_OUTLIER,
        regulation="BRSR Principle 6 (Environmental Impact)",
        requirement=(
            "Companies must minimize environmental footprint. "
            "Scope 1 & 2 emissions must be within industry deviation limits."
        ),
        recommended_action="Immediate Environmental Impact Assessment (EIA) required.",
    ),
    IssueType.REPORTING_GAP: RegulatoryContext(
        issue_type=IssueType.REPORTING_GAP,
        regulation="SEBI BRSR Core - Mandatory Disclosure",
        requirement=(
            "Listed entities must disclose social diversity metrics "
            "(Gender, Differently-abled). Null values are non-compliant."
        ),
        recommended_action="Issue 'Notice of Non-Disclosure' and request data within 7 days.",
    ),
    IssueType.LOGICAL_ANOMALY: RegulatoryContext(
        issue_type=IssueType.LOGICAL_ANOMALY,
        regulation="International Audit Standard (ISA) 240",
        requirement=(
            "Data integrity checks must flag physically impossible values "
            "(e.g., Zero Water Usage in Mfg)."
        ),
        recommended_action="Forensic Audit Flag: Potential Greenwashing or Sensor Failure.",
    ),
}
