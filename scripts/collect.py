"""CLI entrypoint that orchestrates Phase 1 collectors.

Usage:
    uv run python scripts/collect.py --source ergast
    uv run python scripts/collect.py --source wikipedia
    uv run python scripts/collect.py --source fia
    uv run python scripts/collect.py --source all
"""

from __future__ import annotations

import argparse
import sys

from ingestion.collect import ergast, wikipedia

SOURCES = ("ergast", "wikipedia", "fia", "all")


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect raw F1 data for the RAG corpus.")
    parser.add_argument(
        "--source",
        required=True,
        choices=SOURCES,
        help="Which source to collect (or 'all').",
    )
    args = parser.parse_args()

    if args.source in ("ergast", "all"):
        ergast.collect()
    if args.source in ("wikipedia", "all"):
        wikipedia.collect()
    if args.source in ("fia", "all"):
        print("FIA collector not yet implemented (Phase 1, next step).", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
