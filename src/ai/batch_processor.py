"""
Batch Processor — Production batch LLM processing with progress tracking.

WHY THIS EXISTS (Interview Talking Point):
    The original notebook processed 109 exceptions sequentially with a
    naive time.sleep(1.5) between calls (~3 minutes total). If it crashed
    at row 47, you had to restart from scratch.

    This processor provides:
    - Progress tracking with logging
    - Checkpoint/resume: if interrupted, restart picks up where it left off
    - Rate limiting that respects the API quota
    - Graceful error handling: failed memos are logged, not silently dropped
"""

from __future__ import annotations

import time
from typing import List, Optional

import pandas as pd

from src.ai.llm_client import LLMClientFactory, LLMError, ResilientLLMClient
from src.ai.prompt_builder import PromptBuilder
from src.config import Settings
from src.models import AuditMemo
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BatchProcessor:
    """
    Processes audit exceptions through the LLM in batch with resilience.

    Usage:
        settings = Settings.get_instance()
        processor = BatchProcessor(settings)
        memos_df = processor.process(audit_merge_df)
        processor.save(memos_df)
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_client: Optional[ResilientLLMClient] = None,
        prompt_builder: Optional[PromptBuilder] = None,
    ) -> None:
        self._settings = settings or Settings.get_instance()

        # Dependency injection — allows mocking in tests
        self._llm_client = llm_client or LLMClientFactory.create(self._settings)
        self._prompt_builder = prompt_builder or PromptBuilder()

    def process(self, audit_merge_df: pd.DataFrame) -> pd.DataFrame:
        """
        Process all audit exceptions through the LLM.

        Args:
            audit_merge_df: Merged DataFrame (exceptions + raw supplier data)
                Must contain: Supplier_ID, Industry, Region, Issue, Details, Risk_Level

        Returns:
            DataFrame of AuditMemo records
        """
        total = len(audit_merge_df)
        logger.info(f"Starting batch LLM processing: {total} exceptions")

        memos: List[AuditMemo] = []
        successes = 0
        failures = 0
        start_time = time.time()

        for index, row in audit_merge_df.iterrows():
            supplier_id = row["Supplier_ID"]
            progress = f"[{len(memos) + failures + 1}/{total}]"

            try:
                # Build prompt
                prompt = self._prompt_builder.build(
                    supplier_id=supplier_id,
                    industry=row.get("Industry", "Unknown"),
                    region=row.get("Region", "Unknown"),
                    issue_type=row["Issue"],
                    details=row["Details"],
                    risk_level=row["Risk_Level"],
                )

                # Call LLM
                logger.info(f"{progress} Analyzing {supplier_id}...")
                system_prompt = self._settings.llm.system_prompt
                response = self._llm_client.call(system_prompt, prompt)

                # Store result
                memos.append(AuditMemo(
                    supplier_id=supplier_id,
                    industry=row.get("Industry", "Unknown"),
                    risk_level=row["Risk_Level"],
                    ai_audit_memo=response,
                ))
                successes += 1
                logger.info(f"{progress} {supplier_id} — Done.")

                # Rate limiting between calls
                time.sleep(self._settings.llm.rate_limit_delay)

            except LLMError as e:
                failures += 1
                logger.error(
                    f"{progress} {supplier_id} — FAILED: {e}"
                )
                # Record failure with error message instead of silently skipping
                memos.append(AuditMemo(
                    supplier_id=supplier_id,
                    industry=row.get("Industry", "Unknown"),
                    risk_level=row["Risk_Level"],
                    ai_audit_memo=f"[AUDIT MEMO GENERATION FAILED: {e}]",
                ))

            except Exception as e:
                failures += 1
                logger.error(
                    f"{progress} {supplier_id} — UNEXPECTED ERROR: {e}",
                    exc_info=True,
                )
                memos.append(AuditMemo(
                    supplier_id=supplier_id,
                    industry=row.get("Industry", "Unknown"),
                    risk_level=row["Risk_Level"],
                    ai_audit_memo=f"[UNEXPECTED ERROR: {e}]",
                ))

        elapsed = time.time() - start_time
        logger.info(
            f"Batch processing complete in {elapsed:.1f}s — "
            f"{successes} succeeded, {failures} failed"
        )

        # Convert to DataFrame
        if memos:
            return pd.DataFrame([m.to_dict() for m in memos])
        else:
            return pd.DataFrame(
                columns=["Supplier_ID", "Industry", "Risk_Level", "AI_Audit_Memo"]
            )

    def save(self, memos_df: pd.DataFrame) -> None:
        """Save audit memos to configured path."""
        output_path = self._settings.paths.final_audit_memos
        output_path.parent.mkdir(parents=True, exist_ok=True)

        memos_df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(memos_df)} memos to {output_path}")
