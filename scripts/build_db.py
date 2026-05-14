"""CLI: build the Ergast SQLite database from Phase 1 JSON files.

Usage:
    uv run python scripts/build_db.py

Idempotent. Drops + recreates data/db/ergast.sqlite each run. ~3-5s.
"""

from __future__ import annotations

from ingestion.build_db.loader import build


def main() -> int:
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
