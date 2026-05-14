"""Narrative RAG pipeline — retrieve top-K chunks + synthesize an answer.

The 'narrative' path of the routed system. For 'structured' questions see
rag/sql_pipeline.py; the merger combines both when the router says 'both'.

The pipeline records which retrieved chunks were actually used in the LLM
prompt vs. retrieved-but-trimmed — Phase 4 surfaces this as the
'retrieved-vs-used' distinction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rag.llm import chat
from rag.prompts import rag_messages
from rag.retriever import RetrievedChunk, retrieve

DEFAULT_TOP_K = 5
DEFAULT_USED_IN_PROMPT = 5  # all retrieved for now; Phase 4 may trim by context budget


@dataclass
class RagResult:
    """Narrative-path answer plus full provenance."""

    question: str
    retrieved_chunks: list[RetrievedChunk]      # all top-K
    used_in_prompt: list[RetrievedChunk]        # subset actually passed to the LLM
    answer: str


def answer_narrative(
    question: str,
    *,
    top_k: int = DEFAULT_TOP_K,
    used_in_prompt: int = DEFAULT_USED_IN_PROMPT,
) -> RagResult:
    """Run the narrative RAG path: retrieve -> synthesize -> return."""
    retrieved = retrieve(question, top_k=top_k)
    used = retrieved[:used_in_prompt]

    chunks_for_prompt: list[dict[str, Any]] = [
        {
            "text": c.text,
            "title": c.metadata.get("title"),
            "source": c.metadata.get("source"),
        }
        for c in used
    ]
    messages = rag_messages(question, chunks_for_prompt)
    answer = chat(messages)

    return RagResult(
        question=question,
        retrieved_chunks=retrieved,
        used_in_prompt=used,
        answer=answer,
    )
