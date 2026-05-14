"""Shared helpers for Phase 2 chunkers (wikipedia, fia).

Centralizes: tiktoken encoder, chunks.jsonl I/O, resumability lookup,
path normalization. Each per-source chunker module imports these.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import tiktoken

# OpenAI text-embedding-3-small uses the cl100k_base tokenizer.
# We use it for token-count verification + future dry-run cost estimates.
ENCODING_NAME = "cl100k_base"

CHUNKS_PATH = Path("data/chunks/chunks.jsonl")

_encoder: tiktoken.Encoding | None = None


def get_encoder() -> tiktoken.Encoding:
    """Lazily initialize and return the shared tiktoken encoder."""
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding(ENCODING_NAME)
    return _encoder


def count_tokens(text: str) -> int:
    """Count tokens for the configured embedding model's tokenizer."""
    return len(get_encoder().encode(text))


def normalize_path(p: str | Path) -> str:
    """Forward-slash, project-relative path string for cross-platform consistency."""
    return str(p).replace("\\", "/")


def append_chunk(record: dict[str, Any]) -> None:
    """Append one chunk record (as JSON) to data/chunks/chunks.jsonl."""
    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CHUNKS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def existing_chunk_ids(source: str | None = None) -> set[str]:
    """Return the set of chunk_ids already in chunks.jsonl, optionally filtered by source.

    Used for resumability: chunkers skip chunks already emitted.
    """
    if not CHUNKS_PATH.exists():
        return set()
    out: set[str] = set()
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if source is not None and record.get("source") != source:
                continue
            cid = record.get("chunk_id")
            if cid:
                out.add(cid)
    return out
