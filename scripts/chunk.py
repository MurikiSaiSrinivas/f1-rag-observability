"""CLI entrypoint that orchestrates Phase 2 chunkers.

Usage:
    uv run python scripts/chunk.py --source wikipedia
    uv run python scripts/chunk.py --source fia
    uv run python scripts/chunk.py --source all

Each chunker writes to data/chunks/chunks.jsonl and is resumable
(existing chunk_ids are skipped on re-run).
"""

from __future__ import annotations

import argparse

from ingestion.chunk import fia, wikipedia

SOURCES = ("wikipedia", "fia", "all")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Chunk the Phase 1 corpus into retrievable units.",
    )
    parser.add_argument(
        "--source",
        required=True,
        choices=SOURCES,
        help="Which source to chunk (or 'all').",
    )
    args = parser.parse_args()

    if args.source in ("wikipedia", "all"):
        wikipedia.collect()
    if args.source in ("fia", "all"):
        fia.collect()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
