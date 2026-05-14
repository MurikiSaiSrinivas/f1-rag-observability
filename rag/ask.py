"""Top-level ask() — orchestrates the routed RAG / SQL / merger pipeline.

Single public function: ask(question) -> MergedAnswer.

Flow:
1. Router classifies question (structured / narrative / both).
2. Based on category, dispatch:
   - narrative -> RAG pipeline only
   - structured -> SQL pipeline only
   - both -> RAG + SQL in sequence
3. Merger combines results into one final prose answer.
4. MergedAnswer carries every intermediate state (route, retrieved chunks,
   SQL query, SQL rows, final answer) — ready for Phase 4 span emission.

Sequential execution for 'both' (RAG then SQL) keeps the code simple; total
latency ~4s. Phase 4 can parallelize if the dashboard's latency view shows
it's worth the complexity.
"""

from __future__ import annotations

from rag.merger import MergedAnswer, merge
from rag.rag_pipeline import RagResult, answer_narrative
from rag.router import classify
from rag.sql_pipeline import SqlResult, answer_structured


def ask(question: str) -> MergedAnswer:
    """End-to-end Q&A: route -> dispatch -> merge."""
    route = classify(question)

    rag_result: RagResult | None = None
    sql_result: SqlResult | None = None

    if route.category in ("narrative", "both"):
        rag_result = answer_narrative(question)
    if route.category in ("structured", "both"):
        sql_result = answer_structured(question)

    return merge(question, route, rag_result, sql_result)
