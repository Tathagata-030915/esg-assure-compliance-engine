"""
Prompt Builder — Structured prompt engineering for audit memo generation.

WHY THIS EXISTS (Interview Talking Point):
    The original prompt was built with a single f-string buried inside a
    notebook cell. This makes prompts:
    - Untestable (you can't unit test an f-string inside a function)
    - Fragile (one typo in the f-string silently corrupts all memos)
    - Non-reusable (can't swap prompt templates for different regulations)

    This module treats prompt engineering as code: prompts are built
    programmatically with validated inputs, regulatory context injection,
    and structured output format specification.
"""

from __future__ import annotations

from src.models import AuditException, IssueType, RegulatoryContext, REGULATORY_CONTEXT_MAP
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PromptBuilder:
    """
    Constructs structured audit prompts from exception data + regulatory context.

    The builder separates prompt construction from LLM invocation,
    making prompts independently testable and versionable.
    """

    def __init__(
        self,
        regulatory_map: dict[IssueType, RegulatoryContext] | None = None,
    ) -> None:
        self._regulatory_map = regulatory_map or REGULATORY_CONTEXT_MAP

    def build(
        self,
        supplier_id: str,
        industry: str,
        region: str,
        issue_type: str,
        details: str,
        risk_level: str,
    ) -> str:
        """
        Build a structured audit prompt from supplier + exception data.

        Args:
            supplier_id: e.g., "SUP-1064"
            industry: e.g., "IT Services"
            region: e.g., "EMEA"
            issue_type: e.g., "Carbon Outlier"
            details: e.g., "Emissions (2735.41) far exceed industry avg (460.8)"
            risk_level: e.g., "High"

        Returns:
            Formatted prompt string ready for LLM submission
        """
        # Resolve regulatory context
        try:
            issue_enum = IssueType(issue_type)
            context = self._regulatory_map.get(issue_enum)
        except ValueError:
            context = None
            logger.warning(
                f"No regulatory context found for issue type: {issue_type}"
            )

        regulation = context.regulation if context else "General ESG Standards"
        requirement = context.requirement if context else "N/A"
        action = context.recommended_action if context else "Further investigation required."

        prompt = f"""ACT AS: Senior ESG Risk Auditor at EY.

TASK: Write a formal 'Audit Observation Memo' for the following supplier.

--- DATA CONTEXT ---
Supplier ID: {supplier_id}
Industry: {industry}
Region: {region}
Detected Issue: {issue_type}
Specific Details: {details}

--- REGULATORY STANDARD ---
Violated Regulation: {regulation}
Requirement: {requirement}
Recommended Action: {action}

--- OUTPUT FORMAT ---
Title: [Formal Audit Title]
Severity: {risk_level}
Observation: [2-3 sentences explaining the breach technically]
Regulatory Implication: [Cite the specific regulation mentioned above]
Next Steps: [Actionable advice for the client]"""

        return prompt
