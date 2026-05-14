"""CLI entrypoint to load Phase 2 chunks + embeddings into Chroma.

Usage:
    uv run python scripts/index.py

Idempotent. Reads:
- data/chunks/chunks.jsonl
- data/chunks/embeddings.jsonl
Writes:
- data/index/chroma/  (persistent Chroma store)
"""

from __future__ import annotations

from ingestion.index.chroma import index_all


def main() -> int:
    index_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
