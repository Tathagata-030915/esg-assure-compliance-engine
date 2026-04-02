"""
Audit Rule Protocol — The interface that all audit rules must implement.

WHY THIS EXISTS (Interview Talking Point):
    The original audit_analysis.py had 3 hardcoded if/else blocks using
    slow iterrows() loops. Adding a new audit rule required modifying
    the monolithic script — a violation of the Open/Closed Principle.

    This protocol defines the contract for audit rules. Any class that
    implements this interface can be plugged into the AuditEngine without
    modifying engine code. This mirrors how enterprise GRC platforms
    (ServiceNow, SAP) handle regulatory updates.

Design Patterns Used:
    - Strategy Pattern: Each rule is an independent strategy
    - Open/Closed Principle: New rules = new files, zero engine changes
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

import pandas as pd

from src.models import AuditException


class AuditRule(ABC):
    """
    Protocol for audit rules.
    Each rule analyzes a supplier DataFrame and returns detected exceptions.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable rule name for logging and reporting."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """What this rule checks for — used in audit reports."""
        ...

    @abstractmethod
    def evaluate(self, df: pd.DataFrame) -> List[AuditException]:
        """
        Evaluate the rule against the full supplier dataset.

        Args:
            df: Supplier DataFrame with standard column schema

        Returns:
            List of AuditException objects for flagged suppliers
        """
        ...
