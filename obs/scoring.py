"""Answer-quality scoring (4.5), run async after the response (D4.2).

Architecture note / deferred sub-decision: the locked design names RAGAS. The
`ragas` package drags in datasets/langchain and issues its own LLM calls —
heavy and version-fragile. We implement the SAME metrics (faithfulness,
answer_relevancy, context_relevancy) as a single structured gpt-4o-mini
LLM-as-judge call behind the `score_request` seam; swapping in real RAGAS
later is localized. Tracked in docs/decisions.md.
"""

from __future__ import annotations

from obs import db, persist
from obs.flagging import evaluate as run_flags
from rag.llm import chat_json_with_usage

_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "faithfulness": {"type": "number"},
        "answer_relevancy": {"type": "number"},
        "context_relevancy": {"type": "number"},
        "rationale": {"type": "string"},
    },
    "required": [
        "faithfulness",
        "answer_relevancy",
        "context_relevancy",
        "rationale",
    ],
}

_SYS = (
    "You are a strict RAG answer evaluator. Given a QUESTION, the CONTEXT the "
    "system was allowed to use, and the ANSWER, score 0.0–1.0:\n"
    "- faithfulness: is every claim in the ANSWER supported by CONTEXT?\n"
    "- answer_relevancy: does the ANSWER address the QUESTION?\n"
    "- context_relevancy: was the CONTEXT relevant to the QUESTION?\n"
    "Be harsh on unsupported claims. Return JSON only."
)


def _context_for(request_id: str) -> str:
    chunks = db.fetchall(
        """
        SELECT c.text FROM request_chunks rc
        JOIN chunks c ON c.chunk_id=rc.chunk_id
        WHERE rc.request_id=%s AND rc.used_in_prompt=true ORDER BY rc.rank
        """,
        (request_id,),
    )
    parts = [c["text"] for c in chunks]
    sx = db.fetchone(
        "SELECT generated_sql, result_rows FROM sql_executions WHERE request_id=%s",
        (request_id,),
    )
    if sx:
        parts.append(f"SQL: {sx['generated_sql']}\nROWS: {sx['result_rows']}")
    return "\n\n".join(parts) if parts else "(no context retrieved)"


def score_request(request_id: str) -> None:
    """LLM-judge scoring → scores table, then run flag rules. Best-effort:
    swallows errors so a scoring hiccup never corrupts the trace."""
    try:
        r = db.fetchone(
            "SELECT question, final_answer, final_status FROM requests "
            "WHERE request_id=%s",
            (request_id,),
        )
        if not r or r["final_status"] == "refused":
            run_flags(request_id)
            return
        ctx = _context_for(request_id)
        out, _ = chat_json_with_usage(
            [
                {"role": "system", "content": _SYS},
                {
                    "role": "user",
                    "content": (
                        f"QUESTION:\n{r['question']}\n\n"
                        f"CONTEXT:\n{ctx[:6000]}\n\n"
                        f"ANSWER:\n{r['final_answer']}"
                    ),
                },
            ],
            schema=_SCHEMA,
            schema_name="ragas_scores",
        )
        persist.save_scores(
            request_id,
            [
                {"metric": "faithfulness", "value": float(out["faithfulness"]), "scorer_model": "gpt-4o-mini"},
                {"metric": "answer_relevancy", "value": float(out["answer_relevancy"]), "scorer_model": "gpt-4o-mini"},
                {"metric": "context_relevancy", "value": float(out["context_relevancy"]), "scorer_model": "gpt-4o-mini"},
            ],
        )
    except Exception:  # noqa: BLE001 — scoring must never break the request
        pass
    finally:
        run_flags(request_id)
