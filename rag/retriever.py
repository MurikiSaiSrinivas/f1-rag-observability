"""Thin Chroma retriever wrapper.

Embeds a question via OpenAI text-embedding-3-small (same model used for the
corpus) and queries the persistent Chroma collection for top-K chunks with
their metadata.

Single public function: retrieve(question, top_k). Module-level caches keep
the OpenAI + Chroma clients alive across calls for fast repeated retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import chromadb
from openai import OpenAI

CHROMA_PATH = "data/index/chroma"
COLLECTION_NAME = "f1_corpus"
EMBEDDING_MODEL = "text-embedding-3-small"

_openai_client: OpenAI | None = None
_chroma_collection: Any = None


@dataclass
class RetrievedChunk:
    """One chunk pulled from Chroma. similarity is 1 - cosine_distance (higher = more relevant)."""

    chunk_id: str
    similarity: float
    text: str
    metadata: dict[str, Any]


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI()
    return _openai_client


def _get_collection() -> Any:
    global _chroma_collection
    if _chroma_collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        _chroma_collection = client.get_collection(COLLECTION_NAME)
    return _chroma_collection


def embed_query(question: str) -> list[float]:
    """Embed a single question. ~1 token, ~$0.0000002 — free under our token-sharing setup."""
    response = _get_openai_client().embeddings.create(
        model=EMBEDDING_MODEL,
        input=[question],
    )
    return response.data[0].embedding


def retrieve(question: str, top_k: int = 5) -> list[RetrievedChunk]:
    """Embed the question and pull top-K chunks from Chroma."""
    embedding = embed_query(question)
    collection = _get_collection()
    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
    )
    out: list[RetrievedChunk] = []
    for chunk_id, dist, text, meta in zip(
        results["ids"][0],
        results["distances"][0],
        results["documents"][0],
        results["metadatas"][0],
    ):
        out.append(
            RetrievedChunk(
                chunk_id=chunk_id,
                similarity=1.0 - dist,
                text=text,
                metadata=meta,
            )
        )
    return out
