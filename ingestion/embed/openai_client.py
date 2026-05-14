"""OpenAI embedding pipeline.

Reads chunks from data/chunks/chunks.jsonl, embeds them with OpenAI's
text-embedding-3-small model, and writes (chunk_id, model, embedding) rows
to data/chunks/embeddings.jsonl.

Dry-run mode (default) counts tokens via tiktoken and prints a cost estimate
without calling the API. --confirm triggers actual embedding.

Resumable: chunks already present in embeddings.jsonl are skipped.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Iterator

from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from tqdm import tqdm

from ingestion._log import configure_embed_logger
from ingestion.chunk._common import CHUNKS_PATH

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
EMBEDDING_COST_PER_1M_TOKENS = 0.02  # USD; current text-embedding-3-small pricing

# Batch size — OpenAI accepts arrays of inputs per call. Batching is critical:
# 100 calls of 100 chunks each is ~10x faster than 10,000 single-input calls.
BATCH_SIZE = 100

# Rough per-batch retry policy. OpenAI's API is generally stable but rate-limit
# or transient 5xx errors happen; we retry with exponential backoff.
MAX_RETRY_ATTEMPTS = 5

EMBEDDINGS_PATH = Path("data/chunks/embeddings.jsonl")

log = logging.getLogger("ingestion.embed.openai")


def _configure_logger() -> Path:
    """Configure the embed logger."""
    return configure_embed_logger("openai")


def load_chunks() -> list[dict]:
    """Load all chunks from data/chunks/chunks.jsonl into memory.

    Corpus is ~5K rows / ~50MB; in-memory is fine. Returns list of dicts.
    """
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"{CHUNKS_PATH} not found. Run scripts/chunk.py first.")
    out: list[dict] = []
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        for line in f:
            out.append(json.loads(line))
    return out


def existing_embedding_ids() -> set[str]:
    """Return chunk_ids already present in embeddings.jsonl (for resumability)."""
    if not EMBEDDINGS_PATH.exists():
        return set()
    out: set[str] = set()
    with EMBEDDINGS_PATH.open(encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid = record.get("chunk_id")
            if cid:
                out.add(cid)
    return out


def _append_embedding(chunk_id: str, embedding: list[float]) -> None:
    """Append one embedding row to embeddings.jsonl."""
    EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EMBEDDINGS_PATH.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "chunk_id": chunk_id,
                    "model": EMBEDDING_MODEL,
                    "embedding": embedding,
                }
            )
            + "\n"
        )


@retry(
    stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _embed_batch(client: OpenAI, texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. One API call. Retried on transient failures."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [d.embedding for d in response.data]


def _batches(items: list, size: int) -> Iterator[list]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def dry_run(chunks: list[dict]) -> None:
    """Print embedding plan and cost estimate without calling the API."""
    already = existing_embedding_ids()
    pending = [c for c in chunks if c["chunk_id"] not in already]

    total_chunks = len(chunks)
    pending_chunks = len(pending)
    pending_tokens = sum(c["metadata"].get("token_count", 0) for c in pending)
    est_cost = pending_tokens / 1_000_000 * EMBEDDING_COST_PER_1M_TOKENS
    batches = (pending_chunks + BATCH_SIZE - 1) // BATCH_SIZE

    print("=" * 60)
    print(f"  Embedding dry-run — model: {EMBEDDING_MODEL}")
    print("=" * 60)
    print(f"  Total chunks in chunks.jsonl       : {total_chunks:>9,}")
    print(f"  Already embedded (skip)            : {len(already):>9,}")
    print(f"  Pending to embed                   : {pending_chunks:>9,}")
    print(f"  Pending tokens (tiktoken estimate) : {pending_tokens:>9,}")
    print(f"  API calls needed (batch size {BATCH_SIZE:>3}) : {batches:>9,}")
    print(f"  Estimated cost @ ${EMBEDDING_COST_PER_1M_TOKENS}/1M tokens: ${est_cost:.4f}")
    print("=" * 60)

    if pending_chunks == 0:
        print("  Nothing to embed. All chunks already have embeddings.")
    else:
        by_source: dict[str, int] = {}
        for c in pending:
            by_source[c["source"]] = by_source.get(c["source"], 0) + 1
        print("  Pending by source:")
        for src, n in sorted(by_source.items()):
            print(f"    {src:<12s} {n:>6,}")
        print()
        print("  Re-run with --confirm to actually embed.")
        print("  Requires OPENAI_API_KEY in .env (or environment).")


def run_embed() -> None:
    """Actually call the OpenAI API to embed all pending chunks."""
    log_path = _configure_logger()
    print(f"[embed] log file: {log_path}", file=sys.stderr)
    log.info("Embed run started, model=%s", EMBEDDING_MODEL)

    if not os.environ.get("OPENAI_API_KEY"):
        msg = (
            "OPENAI_API_KEY is not set. Add it to .env in the project root "
            "(see .env.example) or export it before running."
        )
        log.error(msg)
        print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(2)

    chunks = load_chunks()
    already = existing_embedding_ids()
    pending = [c for c in chunks if c["chunk_id"] not in already]

    log.info(
        "Chunks: %d total. %d already embedded. %d pending.",
        len(chunks),
        len(already),
        len(pending),
    )

    if not pending:
        log.info("Nothing to embed. Exiting.")
        print("Nothing to embed (all chunks already have embeddings).")
        return

    client = OpenAI()
    total_tokens_used = 0
    started = time.monotonic()

    with tqdm(total=len(pending), desc="Embedding chunks", unit="chunk") as pbar:
        for batch in _batches(pending, BATCH_SIZE):
            texts = [c["text"] for c in batch]
            embeddings = _embed_batch(client, texts)
            if len(embeddings) != len(batch):
                msg = f"Embedding count mismatch: got {len(embeddings)} for {len(batch)} inputs"
                log.error(msg)
                raise RuntimeError(msg)

            for chunk, emb in zip(batch, embeddings):
                if len(emb) != EMBEDDING_DIM:
                    log.warning(
                        "Unexpected embedding dim for %s: %d (expected %d)",
                        chunk["chunk_id"],
                        len(emb),
                        EMBEDDING_DIM,
                    )
                _append_embedding(chunk["chunk_id"], emb)

            batch_tokens = sum(c["metadata"].get("token_count", 0) for c in batch)
            total_tokens_used += batch_tokens
            pbar.update(len(batch))

    elapsed = time.monotonic() - started
    est_cost = total_tokens_used / 1_000_000 * EMBEDDING_COST_PER_1M_TOKENS
    log.info(
        "Embed run finished. Pending: %d. Tokens (estimate): %d. Elapsed: %.1fs. Cost ~$%.4f.",
        len(pending),
        total_tokens_used,
        elapsed,
        est_cost,
    )
    print(
        f"Done. Embedded {len(pending):,} chunks, "
        f"{total_tokens_used:,} tokens, "
        f"~${est_cost:.4f}, "
        f"in {elapsed:.1f}s."
    )
