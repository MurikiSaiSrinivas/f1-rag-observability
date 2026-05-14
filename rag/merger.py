"""Answer merger — combine SQL and/or RAG results into one final prose answer.

The merger is the join point for the routed pipeline. Logic by route:

- "narrative" → RAG answer is already prose; return it as-is. No LLM call.
- "structured" → SQL returned rows; one LLM call formats them into prose.
- "both"       → SQL rows + RAG chunks; one LLM call combines them with
                 SQL facts as authoritative + RAG as context.

The structured + both cases share the same merger prompt; the structured-only
case just passes an empty chunks list. Phase 4 will surface this as one of
the "answer_synthesis" spans.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rag.llm import chat
from rag.prompts import merger_messages
from rag.rag_pipeline import RagResult
from rag.router import RouteDecision
from rag.sql_pipeline import SqlResult


@dataclass
class MergedAnswer:
    """Final user-facing answer plus all intermediate state for Phase 4 traces."""

    question: str
    final_answer: str
    route: RouteDecision
    rag_result: RagResult | None
    sql_result: SqlResult | None


def merge(
    question: str,
    route: RouteDecision,
    rag_result: RagResult | None,
    sql_result: SqlResult | None,
) -> MergedAnswer:
    """Combine path outputs into one prose answer."""
    if route.category == "narrative":
        # RAG result is already a prose answer from the synthesis call.
        final = rag_result.answer if rag_result else "(no answer — narrative path produced nothing)"
        return MergedAnswer(question, final, route, rag_result, sql_result)

    # Structured or both: invoke the merger LLM with SQL output + (optional) chunks.
    chunks_for_prompt: list[dict[str, Any]] = []
    if rag_result is not None:
        chunks_for_prompt = [
            {
                "text": c.text,
                "title": c.metadata.get("title"),
                "source": c.metadata.get("source"),
            }
            for c in rag_result.used_in_prompt
        ]

    if sql_result is None:
        # Defensive — shouldn't happen for structured/both routes
        final = "(no answer — structured path produced no SQL result)"
        return MergedAnswer(question, final, route, rag_result, sql_result)

    messages = merger_messages(
        question=question,
        sql_query=sql_result.sql,
        sql_rows=sql_result.rows,
        chunks=chunks_for_prompt,
    )
    final = chat(messages)
    return MergedAnswer(question, final, route, rag_result, sql_result)
