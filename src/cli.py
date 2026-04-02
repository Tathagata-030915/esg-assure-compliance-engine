"""
CLI Interface — Professional command-line entrypoint for the ESG-Assure engine.

Usage:
    python -m src.cli generate          # Stage 1: Generate supplier data
    python -m src.cli audit             # Stage 2: Run audit rules
    python -m src.cli ai-memo           # Stage 3: Generate AI memos
    python -m src.cli build-dashboard   # Stage 4: Build dashboard data
    python -m src.cli run-all           # Run full pipeline
"""

from __future__ import annotations

import argparse
import sys

from src.config import Settings
from src.pipeline import Pipeline
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="esg-assure",
        description=(
            "ESG-Assure: GenAI-Powered Supplier Risk & "
            "Regulatory Compliance Engine"
        ),
    )

    subparsers = parser.add_subparsers(dest="command", help="Pipeline stage to run")

    # Stage 1: Generate
    subparsers.add_parser(
        "generate",
        help="Generate synthetic supplier data with injected anomalies",
    )

    # Stage 2: Audit
    subparsers.add_parser(
        "audit",
        help="Run statistical audit rules to flag exceptions",
    )

    # Stage 3: AI Memo
    subparsers.add_parser(
        "ai-memo",
        help="Generate AI audit memos for flagged suppliers",
    )

    # Stage 4: Build Dashboard
    subparsers.add_parser(
        "build-dashboard",
        help="Build dashboard master data (merge all artifacts)",
    )

    # Run All
    subparsers.add_parser(
        "run-all",
        help="Execute the full 4-stage pipeline",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    settings = Settings.get_instance()
    pipeline = Pipeline(settings)

    try:
        if args.command == "generate":
            pipeline.stage_generate()

        elif args.command == "audit":
            pipeline.stage_audit()

        elif args.command == "ai-memo":
            pipeline.stage_ai_memo()

        elif args.command == "build-dashboard":
            pipeline.stage_build_dashboard()

        elif args.command == "run-all":
            pipeline.run_all()

        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user.")
        sys.exit(130)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
