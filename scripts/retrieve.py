"""Smoke-test retrieval: embed a question and pull top-K chunks from Chroma.

This is a Phase 2 sanity check — there is no LLM in the loop yet. The point
is to confirm the indexed corpus returns sensible chunks for known questions.

Usage:
    uv run python scripts/retrieve.py
    uv run python scripts/retrieve.py "your question here"
    uv run python scripts/retrieve.py "your question" --k 10
"""

from __future__ import annotations

import argparse
import os
import sys

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

CHROMA_PATH = "data/index/chroma"
COLLECTION_NAME = "f1_corpus"
EMBEDDING_MODEL = "text-embedding-3-small"

DEFAULT_QUESTION = "Who won the 2023 Bahrain Grand Prix?"
DEFAULT_TOP_K = 5


def embed_query(client: OpenAI, question: str) -> list[float]:
    """Embed one question via OpenAI. ~1 input token => ~0.0000002 USD."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[question],
    )
    return response.data[0].embedding


def retrieve(question: str, top_k: int) -> int:
    load_dotenv()
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set in .env or environment.", file=sys.stderr)
        return 2

    openai_client = OpenAI()
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
    except Exception:
        print(
            f"ERROR: Chroma collection '{COLLECTION_NAME}' not found at {CHROMA_PATH}. "
            "Run scripts/index.py first.",
            file=sys.stderr,
        )
        return 2

    print(f"Question: {question}")
    print(f"Embedding & querying Chroma (top {top_k})...")
    embedding = embed_query(openai_client, question)

    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
    )

    ids = results["ids"][0]
    distances = results["distances"][0]
    docs = results["documents"][0]
    metas = results["metadatas"][0]

    print()
    print("=" * 80)
    for rank, (chunk_id, dist, doc, meta) in enumerate(
        zip(ids, distances, docs, metas), start=1
    ):
        similarity = 1.0 - dist  # cosine distance -> similarity
        print(f"#{rank}  similarity={similarity:.4f}  source={meta['source']}")
        print(f"      chunk_id : {chunk_id}")
        print(f"      title    : {meta.get('title') or '(none)'}")
        page = meta.get("page_number", -1)
        if isinstance(page, int) and page > 0:
            print(f"      page     : {page}")
        print(f"      file     : {meta.get('source_file_path', '(none)')}")
        snippet = (doc[:250] or "").replace("\n", " ")
        print(f"      text     : {snippet}{'...' if len(doc) > 250 else ''}")
        print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Retrieve top-K chunks for a question (no LLM in the loop).",
    )
    parser.add_argument(
        "question",
        nargs="?",
        default=DEFAULT_QUESTION,
        help="The question to retrieve for. Default: a known race question.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=DEFAULT_TOP_K,
        help=f"Number of chunks to retrieve. Default: {DEFAULT_TOP_K}.",
    )
    args = parser.parse_args()
    return retrieve(args.question, args.k)


if __name__ == "__main__":
    raise SystemExit(main())
