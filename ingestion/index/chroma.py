"""Chroma index loader.

Reads chunks from data/chunks/chunks.jsonl + pre-computed embeddings from
data/chunks/embeddings.jsonl and upserts them into a persistent Chroma
collection at data/index/chroma/.

Idempotent: re-runs upsert (existing IDs replaced, new IDs added). Safe.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import chromadb
from tqdm import tqdm

from ingestion._log import configure_index_logger

CHROMA_PATH = Path("data/index/chroma")
COLLECTION_NAME = "f1_corpus"
CHUNKS_PATH = Path("data/chunks/chunks.jsonl")
EMBEDDINGS_PATH = Path("data/chunks/embeddings.jsonl")

# Chroma supports batch upsert; 500 is a comfortable size — keeps memory
# bounded without paying per-call overhead 10K times.
BATCH_SIZE = 500

# Cosine similarity is the standard choice for OpenAI embeddings.
COLLECTION_METADATA: dict[str, Any] = {"hnsw:space": "cosine"}

log = logging.getLogger("ingestion.index.chroma")


def _load_embeddings() -> dict[str, list[float]]:
    """Map chunk_id -> embedding vector. Loads entire file into memory (~140 MB)."""
    if not EMBEDDINGS_PATH.exists():
        raise FileNotFoundError(
            f"{EMBEDDINGS_PATH} not found. Run scripts/embed.py --confirm first."
        )
    out: dict[str, list[float]] = {}
    with EMBEDDINGS_PATH.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            out[r["chunk_id"]] = r["embedding"]
    return out


def _load_chunks() -> list[dict]:
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(
            f"{CHUNKS_PATH} not found. Run scripts/chunk.py --source all first."
        )
    out: list[dict] = []
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        for line in f:
            out.append(json.loads(line))
    return out


def _build_metadata(chunk: dict) -> dict[str, Any]:
    """Flatten chunk record into Chroma-compatible metadata (scalar values only).

    Chroma's metadata stores scalar primitives (str/int/float/bool). The chunk
    text and embedding are passed separately. None values get replaced with
    sentinels so retrieval-time metadata filters always see comparable types.
    """
    inner = chunk.get("metadata") or {}

    page_number = chunk.get("page_number")
    out: dict[str, Any] = {
        "source": chunk["source"],
        "source_file_path": chunk["source_file_path"],
        "char_start": int(chunk.get("char_start", 0)),
        "char_end": int(chunk.get("char_end", 0)),
        "page_number": int(page_number) if page_number is not None else -1,
        "title": chunk.get("title") or "",
        "url": chunk.get("url") or "",
    }

    # Source-specific keys (season, category, year, doc_type, token_count).
    # Replace None with sentinel so Chroma filters can be applied without type errors.
    for k, v in inner.items():
        if v is None:
            out[k] = -1 if k in ("season", "year", "round") else ""
        else:
            out[k] = v
    return out


def index_all() -> None:
    log_path = configure_index_logger("chroma")
    print(f"[index_chroma] log file: {log_path}", file=sys.stderr)
    log.info("Chroma index started")

    embeddings = _load_embeddings()
    chunks = _load_chunks()
    log.info("Loaded %d embeddings and %d chunks", len(embeddings), len(chunks))

    # Drop chunks lacking an embedding (resumability-after-partial-embed safety)
    missing = [c for c in chunks if c["chunk_id"] not in embeddings]
    if missing:
        log.warning(
            "%d chunks have no embedding — they will be skipped. Re-run embed first.",
            len(missing),
        )
    indexable = [c for c in chunks if c["chunk_id"] in embeddings]
    log.info("Indexing %d chunks into Chroma", len(indexable))

    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata=COLLECTION_METADATA,
    )
    log.info(
        "Connected to collection %r (current count: %d)",
        COLLECTION_NAME,
        collection.count(),
    )

    with tqdm(total=len(indexable), desc="Indexing", unit="chunk") as pbar:
        for i in range(0, len(indexable), BATCH_SIZE):
            batch = indexable[i : i + BATCH_SIZE]
            collection.upsert(
                ids=[c["chunk_id"] for c in batch],
                embeddings=[embeddings[c["chunk_id"]] for c in batch],
                documents=[c["text"] for c in batch],
                metadatas=[_build_metadata(c) for c in batch],
            )
            pbar.update(len(batch))

    final_count = collection.count()
    log.info(
        "Done. Chroma collection %r now contains %d documents.",
        COLLECTION_NAME,
        final_count,
    )
    print(
        f"\nDone. Chroma collection '{COLLECTION_NAME}' now contains {final_count:,} documents."
    )


if __name__ == "__main__":
    index_all()
