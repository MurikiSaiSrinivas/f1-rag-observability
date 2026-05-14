"""Shared helpers for Phase 2 chunkers (wikipedia, fia).

Centralizes: tiktoken encoder, chunks.jsonl I/O, resumability lookup,
path normalization, char-based sliding-window chunking with paragraph-snap.
Each per-source chunker module imports these.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

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


def find_break(text: str, target_pos: int, search_radius: int = 300) -> int:
    """Find a clean break point at or before target_pos.

    Prefers paragraph break ('\\n\\n') > sentence end ('. '). Falls back to
    a hard cut at target_pos. Returns the position AFTER the break (i.e., where
    the next chunk would start).
    """
    lo = max(0, target_pos - search_radius)

    para = text.rfind("\n\n", lo, target_pos)
    if para >= 0:
        return para + 2

    sent = text.rfind(". ", lo, target_pos)
    if sent >= 0:
        return sent + 2

    return target_pos


def sliding_chunks(
    text: str,
    end_pos: int,
    *,
    target_chars: int,
    overlap_chars: int,
    min_chars: int = 200,
    break_search_radius: int = 300,
) -> Iterator[tuple[str, int, int]]:
    """Yield (chunk_text, char_start, char_end) over text[0:end_pos].

    Char-based sliding window with paragraph-snap. Chunks are sized roughly
    `target_chars` with `overlap_chars` overlap. Offsets reference `text`
    (not the stripped chunk), so callers get exact byte positions for UI
    highlighting.

    Chunk text is .strip()-ed; offsets are adjusted to point to the stripped
    range, not the raw window.
    """
    if end_pos <= 0:
        return

    if end_pos <= target_chars:
        stripped = text[:end_pos].strip()
        if len(stripped) >= min_chars:
            offset = text[:end_pos].index(stripped)
            yield stripped, offset, offset + len(stripped)
        return

    pos = 0
    while pos < end_pos:
        target_end = min(pos + target_chars, end_pos)

        if target_end >= end_pos:
            chunk_end = end_pos
        else:
            chunk_end = find_break(text, target_end, search_radius=break_search_radius)
            # If the break was so close to start that the chunk would be tiny,
            # fall back to a hard cut.
            if chunk_end <= pos + min_chars:
                chunk_end = target_end

        raw = text[pos:chunk_end]
        stripped = raw.strip()
        if len(stripped) >= min_chars:
            offset_in_raw = raw.index(stripped)
            actual_start = pos + offset_in_raw
            actual_end = actual_start + len(stripped)
            yield stripped, actual_start, actual_end

        if chunk_end >= end_pos:
            break

        next_pos = chunk_end - overlap_chars
        if next_pos <= pos:
            next_pos = chunk_end  # safety: never go backward
        pos = next_pos
