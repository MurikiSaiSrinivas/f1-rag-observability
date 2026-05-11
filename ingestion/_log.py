"""Logging helper for ingestion collectors — writes per-run logs to logs/."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("logs")


def configure_collector_logger(source: str) -> Path:
    """Configure the `ingestion.collect.{source}` logger to write a fresh log file.

    Creates a new timestamped log file in logs/, attaches a file handler (DEBUG)
    and a stderr handler (WARNING and above). Returns the log file path so the
    caller can surface it to the user.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = LOG_DIR / f"collect_{source}_{timestamp}.log"

    logger = logging.getLogger(f"ingestion.collect.{source}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(file_handler)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(stderr_handler)

    return log_path
