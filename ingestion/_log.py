"""Logging helper for ingestion pipelines — writes per-run logs to logs/."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("logs")


def configure_collector_logger(source: str) -> Path:
    """Configure `ingestion.collect.{source}` logger. Returns log file path."""
    return _configure_phase_logger("collect", source)


def configure_chunk_logger(source: str) -> Path:
    """Configure `ingestion.chunk.{source}` logger. Returns log file path."""
    return _configure_phase_logger("chunk", source)


def configure_embed_logger(source: str) -> Path:
    """Configure `ingestion.embed.{source}` logger. Returns log file path."""
    return _configure_phase_logger("embed", source)


def configure_index_logger(source: str) -> Path:
    """Configure `ingestion.index.{source}` logger. Returns log file path."""
    return _configure_phase_logger("index", source)


def configure_build_db_logger(source: str) -> Path:
    """Configure `ingestion.build_db.{source}` logger. Returns log file path."""
    return _configure_phase_logger("build_db", source)


def _configure_phase_logger(phase: str, source: str) -> Path:
    """Configure `ingestion.{phase}.{source}` logger with a fresh per-run log file.

    File handler at DEBUG, stderr handler at WARNING+. Returns the log file path
    so the caller can surface it to the user.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = LOG_DIR / f"{phase}_{source}_{timestamp}.log"

    logger = logging.getLogger(f"ingestion.{phase}.{source}")
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
