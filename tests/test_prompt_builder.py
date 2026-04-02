"""
Tests for prompt builder — validates prompt construction and regulatory grounding.
"""

import pytest
from src.ai.prompt_builder import PromptBuilder
from src.models import IssueType, RegulatoryContext, REGULATORY_CONTEXT_MAP


class TestPromptBuilder:
    """Tests for structured prompt construction."""

    def setup_method(self):
        self.builder = PromptBuilder()

    def test_builds_valid_prompt(self):
        """A prompt should contain all required sections."""
        prompt = self.builder.build(
            supplier_id="SUP-1064",
            industry="IT Services",
            region="EMEA",
            issue_type="Carbon Outlier",
            details="Emissions (2735.41) far exceed industry avg (460.8)",
            risk_level="High",
        )
        assert "SUP-1064" in prompt
        assert "IT Services" in prompt
        assert "EMEA" in prompt
        assert "Carbon Outlier" in prompt
        assert "2735.41" in prompt
        assert "BRSR Principle 6" in prompt

    def test_injects_correct_regulation(self):
        """Each issue type should inject its specific regulation."""
        for issue_type in IssueType:
            ctx = REGULATORY_CONTEXT_MAP[issue_type]
            prompt = self.builder.build(
                supplier_id="SUP-0001",
                industry="Test",
                region="Test",
                issue_type=str(issue_type),
                details="Test details",
                risk_level="High",
            )
            assert ctx.regulation in prompt
            assert ctx.requirement in prompt

    def test_handles_unknown_issue_type(self):
        """Unknown issue types should fall back to 'General ESG Standards'."""
        prompt = self.builder.build(
            supplier_id="SUP-0001",
            industry="Test",
            region="Test",
            issue_type="Unknown Issue",
            details="Something unexpected",
            risk_level="Medium",
        )
        assert "General ESG Standards" in prompt

    def test_prompt_contains_output_format(self):
        """The prompt should specify expected output structure."""
        prompt = self.builder.build(
            supplier_id="SUP-0001",
            industry="Test",
            region="Test",
            issue_type="Carbon Outlier",
            details="Test",
            risk_level="High",
        )
        assert "OUTPUT FORMAT" in prompt
        assert "Title:" in prompt
        assert "Severity:" in prompt
        assert "Observation:" in prompt
        assert "Regulatory Implication:" in prompt
        assert "Next Steps:" in prompt
