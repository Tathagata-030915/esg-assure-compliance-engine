"""
Structured Logging — Production-grade observability for a compliance engine.

WHY THIS EXISTS (Interview Talking Point):
    The original codebase uses print() for all output. In production:
    - print() output is invisible to monitoring systems (Datadog, CloudWatch)
    - print() has no severity levels — you can't filter errors from info
    - print() has no timestamps — critical for audit trail reconstruction
    - print() has no structured fields — can't query logs by supplier_id

    This module configures Python's logging with:
    - JSON formatting (for log aggregation platforms)
    - Human-readable text formatting (for local development)
    - Consistent field structure across all modules
    - Module-level loggers for fine-grained control
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Optional


class JSONFormatter(logging.Formatter):
    """
    Formats log records as JSON lines — one JSON object per log entry.
    This is the standard for production log aggregation (ELK, Datadog, Splunk).
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Attach any extra fields passed via logger.info("msg", extra={...})
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data

        # Attach exception info if present
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }

        return json.dumps(log_entry, default=str)


class TextFormatter(logging.Formatter):
    """
    Human-readable formatter for local development.
    Uses emoji prefixes for quick visual scanning.
    """

    LEVEL_ICONS = {
        "DEBUG": "🔍",
        "INFO": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "🔥",
    }

    def format(self, record: logging.LogRecord) -> str:
        icon = self.LEVEL_ICONS.get(record.levelname, "📝")
        timestamp = datetime.now().strftime("%H:%M:%S")
        msg = record.getMessage()
        base = f"{icon} [{timestamp}] {record.module}.{record.funcName}: {msg}"

        if record.exc_info and record.exc_info[1]:
            base += f"\n   Exception: {record.exc_info[1]}"

        return base


def get_logger(
    name: str,
    level: Optional[str] = None,
    fmt: Optional[str] = None,
) -> logging.Logger:
    """
    Get a configured logger for a module.

    Args:
        name: Module name (typically __name__)
        level: Override log level (uses config default if None)
        fmt: Override format ("json" or "text", uses config default if None)

    Returns:
        Configured logging.Logger instance

    Usage:
        from src.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Processing supplier", extra={"extra_data": {"id": "SUP-1000"}})
    """
    # Import here to avoid circular imports (config.py doesn't import logger)
    from src.config import Settings
    settings = Settings.get_instance()

    log_level = getattr(logging, (level or settings.log.level).upper(), logging.INFO)
    log_format = fmt or settings.log.format

    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers on repeated calls
    if not logger.handlers:
        logger.setLevel(log_level)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)

        if log_format == "json":
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(TextFormatter())

        logger.addHandler(handler)

    return logger
