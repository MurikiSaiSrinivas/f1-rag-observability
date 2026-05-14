"""FIA regulations chunker — paragraph-aware, page-tracking, per PDF.

For each FIA regulation PDF collected in Phase 1:
1. Re-extract text page-by-page via pypdf (page boundaries are critical for the
   Phase 4 PDF.js viewer).
2. De-hyphenate cross-line word breaks ('tech-\\ntechnical' -> 'technical') —
   conservative regex matches only when the joined char is lowercase.
3. Chunk each page's text with the shared sliding-window helper using
   FIA-tuned parameters (~3000 chars target, ~300 chars overlap).
4. Every chunk records its page_number; source_file_path points at the PDF.

Trade-off: per-page chunking means a paragraph spanning page N -> N+1 is split
into two non-overlapping chunks. Each fragment is still useful for retrieval;
this becomes a candidate Phase 4 failure case if it turns out to matter.

Output appended to data/chunks/chunks.jsonl. Resumable.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

from pypdf import PdfReader
from tqdm import tqdm

from ingestion._log import configure_chunk_logger
from ingestion.chunk._common import (
    append_chunk,
    count_tokens,
    existing_chunk_ids,
    normalize_path,
    sliding_chunks,
)

SOURCE = "fia"
FIA_DIR = Path("data/raw/fia")

# Larger windows than Wikipedia — regulations have long paragraphs and
# heavy cross-referencing; bigger chunks preserve context.
CHUNK_TARGET_CHARS = 3000      # ~750 tokens
OVERLAP_CHARS = 300            # ~75 tokens
MIN_CHUNK_CHARS = 200
BREAK_SEARCH_RADIUS = 400

TOKEN_COUNT_WARN_LOW = 50
TOKEN_COUNT_WARN_HIGH = 1500

EXPECTED_YEARS = list(range(2020, 2026))
EXPECTED_TYPES = ("sporting", "technical")

# Hyphenated line break: 'tech-\ntechnical' -> 'technical'. Only when the next
# char is lowercase, to avoid mangling proper hyphenated terms.
HYPHEN_LINEBREAK_RE = re.compile(r"-\n(?=[a-z])")

log = logging.getLogger("ingestion.chunk.fia")


def _de_hyphenate(text: str) -> str:
    return HYPHEN_LINEBREAK_RE.sub("", text)


def _discover_pdfs() -> list[tuple[int, str, Path]]:
    """Return (year, doc_type, pdf_path) for every FIA PDF present on disk."""
    out: list[tuple[int, str, Path]] = []
    for year in EXPECTED_YEARS:
        for doc_type in EXPECTED_TYPES:
            pdf_path = FIA_DIR / str(year) / f"{doc_type}.pdf"
            if pdf_path.exists():
                out.append((year, doc_type, pdf_path))
    return out


def chunk_one_pdf(
    year: int,
    doc_type: str,
    pdf_path: Path,
    existing_ids: set[str],
) -> tuple[int, int, int]:
    """Chunk one FIA PDF page-by-page.

    Returns (chunks_written, chunks_skipped_existing, pages_processed).
    """
    reader = PdfReader(pdf_path)
    pdf_path_normalized = normalize_path(pdf_path)
    title = f"FIA {doc_type.title()} Regulations {year}"

    written = 0
    skipped = 0
    pages_processed = 0

    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        try:
            page_text = page.extract_text() or ""
        except Exception as e:
            log.warning("Failed to extract page %d of %s: %s", page_num, pdf_path, e)
            continue

        page_text = _de_hyphenate(page_text)
        pages_processed += 1

        if not page_text.strip():
            continue

        for chunk_idx, (chunk_text, start, end) in enumerate(
            sliding_chunks(
                page_text,
                len(page_text),
                target_chars=CHUNK_TARGET_CHARS,
                overlap_chars=OVERLAP_CHARS,
                min_chars=MIN_CHUNK_CHARS,
                break_search_radius=BREAK_SEARCH_RADIUS,
            )
        ):
            chunk_id = f"{SOURCE}/{year}/{doc_type}/p{page_num:03d}#{chunk_idx:02d}"
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
                "source_file_path": pdf_path_normalized,
                "char_start": start,
                "char_end": end,
                "page_number": page_num,
                "text": chunk_text,
                "title": title,
                "url": None,
                "metadata": {
                    "year": year,
                    "doc_type": doc_type,
                    "token_count": token_count,
                },
            }
            append_chunk(record)
            written += 1

    return written, skipped, pages_processed


def collect() -> None:
    log_path = configure_chunk_logger("fia")
    print(f"[chunk_fia] log file: {log_path}", file=sys.stderr)
    log.info("FIA chunker started")

    pdfs = _discover_pdfs()
    existing_ids = existing_chunk_ids(SOURCE)
    log.info(
        "Discovered %d FIA PDFs. Existing fia chunks: %d.",
        len(pdfs),
        len(existing_ids),
    )

    if not pdfs:
        log.error("No FIA PDFs found under %s. See Phase 1 docs.", FIA_DIR)
        return

    total_written = 0
    total_skipped = 0
    total_pages = 0

    for year, doc_type, pdf_path in tqdm(pdfs, desc="FIA PDFs", unit="pdf"):
        try:
            w, s, p = chunk_one_pdf(year, doc_type, pdf_path, existing_ids)
        except Exception as e:
            log.error("Failed on %s: %s", pdf_path, e, exc_info=True)
            continue
        total_written += w
        total_skipped += s
        total_pages += p
        log.info(
            "%s/%s: %d pages, %d new chunks (%d skipped)",
            year, doc_type, p, w, s,
        )

    log.info(
        "FIA chunker finished. PDFs: %d. Pages: %d. New chunks: %d. Skipped: %d.",
        len(pdfs),
        total_pages,
        total_written,
        total_skipped,
    )


if __name__ == "__main__":
    collect()
