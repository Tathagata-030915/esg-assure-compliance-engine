"""
Pipeline Orchestrator — Coordinates the full ETL-A flow.

Stages:
    1. GENERATE: Create synthetic supplier data with anomalies
    2. AUDIT: Apply statistical rules to flag exceptions
    3. AI-MEMO: Generate audit memos via LLM for flagged suppliers
    4. BUILD-DASHBOARD: Merge all data for Power BI consumption
"""

from __future__ import annotations

import time

import pandas as pd

from src.ai.batch_processor import BatchProcessor
from src.config import Settings
from src.engines.audit_engine import AuditEngine
from src.generators.supplier_generator import SupplierGenerator
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Pipeline:
    """
    End-to-end ESG Audit Pipeline orchestrator.

    Each stage is independently runnable and idempotent.

    Usage:
        settings = Settings.get_instance()
        pipeline = Pipeline(settings)
        pipeline.run_all()
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings.get_instance()

    def stage_generate(self) -> pd.DataFrame:
        """Stage 1: Generate synthetic supplier data."""
        logger.info("=" * 60)
        logger.info("STAGE 1: DATA GENERATION")
        logger.info("=" * 60)

        generator = SupplierGenerator(self._settings)
        df = generator.generate()
        generator.save(df)

        return df

    def stage_audit(self, suppliers_df: pd.DataFrame | None = None) -> pd.DataFrame:
        """Stage 2: Run audit rules to detect exceptions."""
        logger.info("=" * 60)
        logger.info("STAGE 2: AUDIT ANALYSIS")
        logger.info("=" * 60)

        if suppliers_df is None:
            path = self._settings.paths.suppliers_raw
            logger.info(f"Loading supplier data from {path}")
            suppliers_df = pd.read_csv(path)

        engine = AuditEngine(self._settings)
        exceptions_df = engine.run(suppliers_df)
        engine.save(exceptions_df)

        return exceptions_df

    def stage_ai_memo(
        self,
        exceptions_df: pd.DataFrame | None = None,
        suppliers_df: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Stage 3: Generate AI audit memos for flagged suppliers."""
        logger.info("=" * 60)
        logger.info("STAGE 3: GenAI AUDIT MEMO GENERATION")
        logger.info("=" * 60)

        if exceptions_df is None:
            path = self._settings.paths.audit_exceptions
            logger.info(f"Loading exceptions from {path}")
            exceptions_df = pd.read_csv(path)

        if suppliers_df is None:
            path = self._settings.paths.suppliers_raw
            logger.info(f"Loading supplier data from {path}")
            suppliers_df = pd.read_csv(path)

        # Merge exceptions with full supplier data
        audit_merge = pd.merge(
            exceptions_df, suppliers_df,
            on="Supplier_ID", how="left"
        )
        logger.info(f"Merged data: {len(audit_merge)} exception records")

        processor = BatchProcessor(self._settings)
        memos_df = processor.process(audit_merge)
        processor.save(memos_df)

        return memos_df

    def stage_build_dashboard(
        self,
        suppliers_df: pd.DataFrame | None = None,
        memos_df: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Stage 4: Build dashboard master data by merging all artifacts."""
        logger.info("=" * 60)
        logger.info("STAGE 4: DASHBOARD DATA BUILD")
        logger.info("=" * 60)

        if suppliers_df is None:
            path = self._settings.paths.suppliers_raw
            suppliers_df = pd.read_csv(path)

        if memos_df is None:
            path = self._settings.paths.final_audit_memos
            memos_df = pd.read_csv(path)

        # Left join: all suppliers + memos for flagged ones
        dashboard = pd.merge(
            suppliers_df,
            memos_df[["Supplier_ID", "Risk_Level", "AI_Audit_Memo"]],
            on="Supplier_ID",
            how="left",
        )

        # Fill compliant suppliers
        dashboard["Risk_Level"] = dashboard["Risk_Level"].fillna("Low/Compliant")
        dashboard["AI_Audit_Memo"] = dashboard["AI_Audit_Memo"].fillna(
            "No Issues Detected - Compliant with BRSR."
        )

        output_path = self._settings.paths.dashboard_master_data
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dashboard.to_csv(output_path, index=False)

        logger.info(
            f"Dashboard master data saved: {len(dashboard)} rows "
            f"to {output_path}"
        )

        return dashboard

    def run_all(self) -> None:
        """Execute the full 4-stage pipeline."""
        pipeline_start = time.time()
        logger.info("Starting full ESG-Assure Pipeline")

        suppliers_df = self.stage_generate()
        exceptions_df = self.stage_audit(suppliers_df)
        memos_df = self.stage_ai_memo(exceptions_df, suppliers_df)
        self.stage_build_dashboard(suppliers_df, memos_df)

        elapsed = time.time() - pipeline_start
        logger.info(
            f"Pipeline complete in {elapsed:.1f}s"
        )
