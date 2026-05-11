"""FIA regulations collector — extract text from manually-downloaded sporting/technical PDFs.

The FIA doesn't expose a clean API for regulation PDFs and the URL structure changes
yearly. So this collector doesn't *download* anything — it processes PDFs that the
user has placed at the expected paths.

Expected file layout (you populate these yourself):
    data/raw/fia/2020/sporting.pdf
    data/raw/fia/2020/technical.pdf
    data/raw/fia/2021/sporting.pdf
    data/raw/fia/2021/technical.pdf
    ...
    data/raw/fia/2025/sporting.pdf
    data/raw/fia/2025/technical.pdf

Source: https://www.fia.com/regulations  (find F1 sporting + technical regs, latest
version per year for 2020-2025). Rename downloads to sporting.pdf / technical.pdf.

For each PDF found, extracts plaintext via pypdf, saves alongside as .txt, and
appends one row per file to data/manifest.jsonl. Resumable: existing .txt files
are skipped.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from tqdm import tqdm

from ingestion._log import configure_collector_logger

DATA_DIR = Path("data/raw/fia")
MANIFEST_PATH = Path("data/manifest.jsonl")

EXPECTED_YEARS = list(range(2020, 2026))
EXPECTED_TYPES = ("sporting", "technical")

log = logging.getLogger("ingestion.collect.fia")


def _extract_text(pdf_path: Path) -> str:
    reader = PdfReader(pdf_path)
    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            log.warning("Page %d of %s: extract_text failed: %s", i + 1, pdf_path, e)
            text = ""
        pages.append(text)
    return "\n\n".join(pages)


def _append_manifest(record: dict[str, Any]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _discover_pdfs() -> tuple[list[tuple[int, str, Path]], list[tuple[int, str, Path]]]:
    """Return (found, missing). Each is a list of (year, doc_type, expected_path)."""
    found: list[tuple[int, str, Path]] = []
    missing: list[tuple[int, str, Path]] = []
    for year in EXPECTED_YEARS:
        for doc_type in EXPECTED_TYPES:
            pdf_path = DATA_DIR / str(year) / f"{doc_type}.pdf"
            if pdf_path.exists():
                found.append((year, doc_type, pdf_path))
            else:
                missing.append((year, doc_type, pdf_path))
    return found, missing


def collect() -> None:
    log_path = configure_collector_logger("fia")
    print(f"[fia] log file: {log_path}", file=sys.stderr)
    log.info("Collector started")

    found, missing = _discover_pdfs()
    total_expected = len(EXPECTED_YEARS) * len(EXPECTED_TYPES)
    log.info("Discovered %d/%d PDFs", len(found), total_expected)

    for _, _, path in missing:
        log.warning("Missing: %s", path)

    if not found:
        log.error(
            "No PDFs found in %s. Place FIA PDFs at data/raw/fia/{year}/{sporting|technical}.pdf "
            "and re-run. See docstring of this module for details.",
            DATA_DIR,
        )
        return

    extracted = 0
    skipped = 0

    for year, doc_type, pdf_path in tqdm(found, desc="FIA PDFs", unit="pdf"):
        txt_path = pdf_path.with_suffix(".txt")
        if txt_path.exists():
            log.debug("Skip (exists): %s", txt_path)
            skipped += 1
            continue

        try:
            text = _extract_text(pdf_path)
        except Exception as e:
            log.error("Failed to extract %s: %s", pdf_path, e)
            continue

        txt_path.write_text(text, encoding="utf-8")
        char_count = len(text)
        _append_manifest(
            {
                "id": f"fia/{year}/{doc_type}",
                "source": "fia",
                "year": year,
                "doc_type": doc_type,
                "pdf_path": str(pdf_path),
                "file_path": str(txt_path),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "char_count": char_count,
            }
        )
        log.info("Extracted %s -> %s (%d chars)", pdf_path, txt_path, char_count)
        extracted += 1

    log.info(
        "Collector finished: extracted=%d, skipped=%d, missing=%d",
        extracted,
        skipped,
        len(missing),
    )


if __name__ == "__main__":
    collect()
