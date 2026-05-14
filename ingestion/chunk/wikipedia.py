"""Wikipedia article chunker — char-based sliding window with paragraph snapping.

For each Wikipedia .txt file collected in Phase 1:
1. Strip end-of-article boilerplate sections (References, External links, etc.).
2. Chunk the remaining content into ~2000-char windows with ~200-char overlap.
3. Snap chunk boundaries to nearest paragraph break (\\n\\n) or sentence end (". ").
4. Record char_start / char_end as byte offsets into the ORIGINAL .txt (not the
   stripped version) — so the Phase 4 dashboard can highlight the exact text.

Output: one row per chunk appended to data/chunks/chunks.jsonl.
Resumable: chunks already emitted (by chunk_id) are skipped.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

from tqdm import tqdm

from ingestion._log import configure_chunk_logger
from ingestion.chunk._common import (
    append_chunk,
    count_tokens,
    existing_chunk_ids,
    normalize_path,
)

SOURCE = "wikipedia"
WIKIPEDIA_DIR = Path("data/raw/wikipedia")
MANIFEST_PATH = Path("data/manifest.jsonl")

# Char-based windowing parameters. Calibrated for ~500 tokens per chunk.
CHUNK_TARGET_CHARS = 2000
OVERLAP_CHARS = 200
MIN_CHUNK_CHARS = 200
BREAK_SEARCH_RADIUS = 300  # how far back to look for a paragraph/sentence break

# Tiktoken sanity bounds — warn if chunks drift far outside ~400-700 tokens.
TOKEN_COUNT_WARN_LOW = 100
TOKEN_COUNT_WARN_HIGH = 1000

# Section headers that reliably mark end-of-article boilerplate.
# 'Notes' is excluded — it appears mid-article as a footnote header in some articles.
BOILERPLATE_HEADERS = frozenset({
    "See also",
    "References",
    "External links",
    "Further reading",
    "Bibliography",
    "Citations",
    "Sources",
})

SEASON_RE = re.compile(r"^(\d{4})_")

log = logging.getLogger("ingestion.chunk.wikipedia")


def _load_manifest() -> dict[str, dict]:
    """Map normalized source_file_path -> {title, url, category} for wikipedia entries."""
    out: dict[str, dict] = {}
    if not MANIFEST_PATH.exists():
        return out
    with MANIFEST_PATH.open(encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("source") != "wikipedia":
                continue
            key = normalize_path(record["file_path"])
            out[key] = {
                "title": record["title"],
                "url": record["url"],
                "category": record["category"],
            }
    return out


def _extract_season(slug: str) -> int | None:
    """Pull a 4-digit season from filenames like '2023_bahrain_grand_prix'."""
    m = SEASON_RE.match(slug)
    return int(m.group(1)) if m else None


def _find_boilerplate_start(text: str) -> int:
    """Return char offset where end-of-article boilerplate begins (or len(text) if none).

    Scans every line; if a line, stripped, EXACTLY matches a boilerplate header, its
    starting offset is a candidate. Returns the earliest candidate.
    """
    earliest = len(text)
    pos = 0
    for line in text.split("\n"):
        if line.strip() in BOILERPLATE_HEADERS and pos < earliest:
            earliest = pos
        pos += len(line) + 1  # +1 for the consumed newline
    return earliest


def _find_break(text: str, target_pos: int) -> int:
    """Find a clean break point at or before target_pos.

    Prefers paragraph break ('\\n\\n') > sentence end ('. '). Falls back to hard
    cut at target_pos. Search window: BREAK_SEARCH_RADIUS chars before target.
    Returns the position AFTER the break (i.e., where the next chunk would start).
    """
    lo = max(0, target_pos - BREAK_SEARCH_RADIUS)

    para = text.rfind("\n\n", lo, target_pos)
    if para >= 0:
        return para + 2

    sent = text.rfind(". ", lo, target_pos)
    if sent >= 0:
        return sent + 2

    return target_pos


def _chunk_with_offsets(text: str, end_pos: int):
    """Yield (chunk_text, char_start, char_end) tuples.

    Chunks text[0:end_pos] into ~CHUNK_TARGET_CHARS windows with OVERLAP_CHARS
    overlap. Offsets point into `text` and reflect the chunk's leading/trailing
    whitespace removed (after .strip()).
    """
    if end_pos <= 0:
        return

    if end_pos <= CHUNK_TARGET_CHARS:
        stripped = text[:end_pos].strip()
        if len(stripped) >= MIN_CHUNK_CHARS:
            offset = text[:end_pos].index(stripped)
            yield stripped, offset, offset + len(stripped)
        return

    pos = 0
    while pos < end_pos:
        target_end = min(pos + CHUNK_TARGET_CHARS, end_pos)

        if target_end >= end_pos:
            chunk_end = end_pos
        else:
            chunk_end = _find_break(text, target_end)
            # If the break was so close to the start that the chunk would be tiny,
            # fall back to a hard cut at the target.
            if chunk_end <= pos + MIN_CHUNK_CHARS:
                chunk_end = target_end

        raw = text[pos:chunk_end]
        stripped = raw.strip()
        if len(stripped) >= MIN_CHUNK_CHARS:
            offset_in_raw = raw.index(stripped)
            actual_start = pos + offset_in_raw
            actual_end = actual_start + len(stripped)
            yield stripped, actual_start, actual_end

        if chunk_end >= end_pos:
            break

        next_pos = chunk_end - OVERLAP_CHARS
        if next_pos <= pos:
            next_pos = chunk_end  # safety: never go backward
        pos = next_pos


def chunk_one_file(
    txt_path: Path,
    meta: dict,
    existing_ids: set[str],
) -> tuple[int, int]:
    """Chunk one Wikipedia .txt file. Returns (new_chunks_written, skipped_existing)."""
    slug = txt_path.stem
    category = meta["category"]
    season = _extract_season(slug)

    text = txt_path.read_text(encoding="utf-8")
    boilerplate_start = _find_boilerplate_start(text)
    if boilerplate_start < len(text):
        log.debug(
            "Boilerplate strip for %s: keeping %d / %d chars",
            slug,
            boilerplate_start,
            len(text),
        )

    written = 0
    skipped = 0
    for idx, (chunk_text, start, end) in enumerate(
        _chunk_with_offsets(text, boilerplate_start)
    ):
        chunk_id = f"{SOURCE}/{category}/{slug}#{idx:04d}"
        if chunk_id in existing_ids:
            skipped += 1
            continue

        token_count = count_tokens(chunk_text)
        if token_count < TOKEN_COUNT_WARN_LOW or token_count > TOKEN_COUNT_WARN_HIGH:
            log.warning(
                "Token count out of range for %s: %d tokens (%d chars)",
                chunk_id,
                token_count,
                len(chunk_text),
            )

        record = {
            "chunk_id": chunk_id,
            "source": SOURCE,
            "source_file_path": normalize_path(txt_path),
            "char_start": start,
            "char_end": end,
            "page_number": None,
            "text": chunk_text,
            "title": meta["title"],
            "url": meta["url"],
            "metadata": {
                "category": category,
                "season": season,
                "token_count": token_count,
            },
        }
        append_chunk(record)
        written += 1
        log.debug(
            "Wrote %s (%d chars, %d tokens, bytes %d-%d)",
            chunk_id,
            len(chunk_text),
            token_count,
            start,
            end,
        )

    if written == 0 and skipped == 0:
        log.warning("No chunks emitted for %s (in-scope chars: %d)", slug, boilerplate_start)

    return written, skipped


def collect() -> None:
    log_path = configure_chunk_logger("wikipedia")
    print(f"[chunk_wikipedia] log file: {log_path}", file=sys.stderr)
    log.info("Wikipedia chunker started")

    manifest = _load_manifest()
    existing_ids = existing_chunk_ids(SOURCE)
    log.info(
        "Manifest entries: %d. Existing wikipedia chunks: %d.",
        len(manifest),
        len(existing_ids),
    )

    files = sorted(WIKIPEDIA_DIR.rglob("*.txt"))
    log.info("Discovered %d wikipedia .txt files", len(files))

    total_written = 0
    total_skipped = 0
    files_missing_meta = 0
    files_failed = 0

    for txt_path in tqdm(files, desc="Wikipedia articles", unit="file"):
        key = normalize_path(txt_path)
        meta = manifest.get(key)
        if meta is None:
            log.warning("No manifest entry for %s — skipping", key)
            files_missing_meta += 1
            continue

        try:
            written, skipped = chunk_one_file(txt_path, meta, existing_ids)
        except Exception as e:
            log.error("Failed to chunk %s: %s", txt_path, e, exc_info=True)
            files_failed += 1
            continue

        total_written += written
        total_skipped += skipped

    log.info(
        "Wikipedia chunker finished. Files: %d. New chunks: %d. Skipped (existing): %d. "
        "Missing manifest: %d. Failed: %d.",
        len(files),
        total_written,
        total_skipped,
        files_missing_meta,
        files_failed,
    )


if __name__ == "__main__":
    collect()
