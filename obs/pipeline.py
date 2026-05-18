"""Instrumented /ask orchestrator (D4.2, D4.3).

Reimplements the routed RAG/SQL flow from rag/ at the primitive level so each
step is its own OpenTelemetry span with real token/cost attributes. The
hand-rolled pipeline (D3.2) is exactly what makes this clean. Returns a
public answer-view dict and persists the full trace to Postgres.
"""

from __future__ import annotations

import uuid
from time import perf_counter
from typing import Any

import tiktoken

from obs import cost, persist
from obs.guardrails import run_input, run_output, run_retrieval
from obs.tracing import span, trace_request
from rag.llm import CHAT_MODEL, chat_json_with_usage, chat_with_usage
from rag.prompts import (
    ROUTER_SCHEMA,
    SQL_SCHEMA,
    merger_messages,
    rag_messages,
    router_messages,
    sql_messages,
)
from rag.retriever import EMBEDDING_MODEL, _get_collection, embed_query
from rag.sql_pipeline import _clean_sql, _execute_sql

TOP_K = 5
USED_IN_PROMPT = 3  # real context-budget trim → meaningful retrieved-vs-used

_enc = tiktoken.get_encoding("cl100k_base")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


def _chunk_rows(retrieved: list[Any]) -> list[dict[str, Any]]:
    """RetrievedChunk → chunk/request_chunk row dicts (sentinels → None)."""
    rows: list[dict[str, Any]] = []
    for rank, c in enumerate(retrieved, start=1):
        m = c.metadata or {}

        def _opt(v: Any) -> Any:
            return None if v in (-1, "", None) else v

        rows.append(
            {
                "chunk_id": c.chunk_id,
                "source": m.get("source", "wikipedia"),
                "source_file_path": m.get("source_file_path", ""),
                "char_start": _opt(m.get("char_start")),
                "char_end": _opt(m.get("char_end")),
                "page_number": _opt(m.get("page_number")),
                "title": m.get("title", ""),
                "url": m.get("url", "") or "",
                "text": c.text,
                "metadata": m,
                "rank": rank,
                "similarity": round(float(c.similarity), 4),
                "used_in_prompt": rank <= USED_IN_PROMPT,
            }
        )
    return rows


def observed_ask(
    question: str,
    client_id: str,
    session_id: str,
    prompt_version: str = "v1",
    *,
    replay_of: str | None = None,
) -> dict[str, Any]:
    request_id = _new_id("req")
    t_start = perf_counter()

    tot_prompt = tot_completion = embed_tokens = 0
    total_cost = 0.0
    route_decision: dict[str, Any] = {}
    chunk_rows: list[dict[str, Any]] = []
    sql_record: dict[str, Any] | None = None
    guardrails: list[dict[str, Any]] = []
    final_answer = ""
    final_status = "success"

    with trace_request() as collector:
        with span(
            "ask", "orchestration", question=question, prompt_version=prompt_version
        ):
            with span("guardrails.input", "guardrail") as gs:
                hits = run_input(question)
                guardrails += hits
                gs.set_attribute(
                    "f1.attrs",
                    __import__("json").dumps(
                        {"triggered": [h["rule_name"] for h in hits]}
                    ),
                )
            if any(h["action"] in ("refuse", "reject", "block") for h in hits):
                final_status = "refused"
                final_answer = (
                    "This question was declined by an input guardrail."
                )
            else:
                # ---- router ----
                with span("router.classify", "llm", model=CHAT_MODEL) as rs:
                    t0 = perf_counter()
                    raw, u = chat_json_with_usage(
                        router_messages(question),
                        schema=ROUTER_SCHEMA,
                        schema_name="route_decision",
                    )
                    router_latency = int((perf_counter() - t0) * 1000)
                    rs.set_attribute("f1.attrs", __import__("json").dumps(
                        {"category": raw["category"],
                         "confidence": raw["confidence"],
                         "tokens": u["total_tokens"]}))
                tot_prompt += u["prompt_tokens"]
                tot_completion += u["completion_tokens"]
                total_cost += cost.chat_cost(
                    CHAT_MODEL, u["prompt_tokens"], u["completion_tokens"]
                )
                route = raw["category"]
                route_decision = {
                    "category": route,
                    "confidence": float(raw["confidence"]),
                    "reasoning": raw["reasoning"],
                    "router_model": CHAT_MODEL,
                    "router_tokens": u["total_tokens"],
                    "router_latency_ms": router_latency,
                }

                rag_answer = ""
                # ---- narrative path ----
                if route in ("narrative", "both"):
                    with span("rag.pipeline", "orchestration"):
                        with span(
                            "rag.embed_query", "retrieval", model=EMBEDDING_MODEL
                        ):
                            q_tokens = len(_enc.encode(question))
                            embed_tokens += q_tokens
                            total_cost += cost.embed_cost(
                                EMBEDDING_MODEL, q_tokens
                            )
                            emb = embed_query(question)
                        with span(
                            "rag.vector_search", "retrieval", top_k=TOP_K
                        ) as vs:
                            res = _get_collection().query(
                                query_embeddings=[emb], n_results=TOP_K
                            )
                            from rag.retriever import RetrievedChunk

                            retrieved = [
                                RetrievedChunk(
                                    chunk_id=cid,
                                    similarity=1.0 - dist,
                                    text=txt,
                                    metadata=meta,
                                )
                                for cid, dist, txt, meta in zip(
                                    res["ids"][0],
                                    res["distances"][0],
                                    res["documents"][0],
                                    res["metadatas"][0],
                                )
                            ]
                            chunk_rows = _chunk_rows(retrieved)
                            vs.set_attribute(
                                "f1.attrs",
                                __import__("json").dumps(
                                    {
                                        "returned": len(retrieved),
                                        "best_similarity": round(
                                            chunk_rows[0]["similarity"], 4
                                        )
                                        if chunk_rows
                                        else 0,
                                    }
                                ),
                            )
                        with span("guardrails.retrieval", "guardrail") as grs:
                            rhits = run_retrieval(chunk_rows)
                            guardrails += rhits
                            grs.set_attribute(
                                "f1.attrs",
                                __import__("json").dumps(
                                    {"triggered": [h["rule_name"] for h in rhits]}
                                ),
                            )
                        used = [c for c in chunk_rows if c["used_in_prompt"]]
                        with span("rag.synthesis", "llm", model=CHAT_MODEL):
                            msgs = rag_messages(
                                question,
                                [
                                    {
                                        "text": c["text"],
                                        "title": c["title"],
                                        "source": c["source"],
                                    }
                                    for c in used
                                ],
                            )
                            rag_answer, u = chat_with_usage(msgs)
                            tot_prompt += u["prompt_tokens"]
                            tot_completion += u["completion_tokens"]
                            total_cost += cost.chat_cost(
                                CHAT_MODEL,
                                u["prompt_tokens"],
                                u["completion_tokens"],
                            )

                # ---- structured path ----
                if route in ("structured", "both"):
                    with span("sql.pipeline", "orchestration"):
                        with span("sql.generate", "llm", model=CHAT_MODEL):
                            t0 = perf_counter()
                            sraw, u = chat_json_with_usage(
                                sql_messages(question),
                                schema=SQL_SCHEMA,
                                schema_name="sql_query",
                            )
                            gen_latency = int((perf_counter() - t0) * 1000)
                            tot_prompt += u["prompt_tokens"]
                            tot_completion += u["completion_tokens"]
                            total_cost += cost.chat_cost(
                                CHAT_MODEL,
                                u["prompt_tokens"],
                                u["completion_tokens"],
                            )
                        gen_sql = sraw["sql"]
                        cleaned = _clean_sql(gen_sql) if gen_sql.strip() else ""
                        with span("sql.execute", "sql") as ses:
                            t0 = perf_counter()
                            if cleaned:
                                rows, err = _execute_sql(gen_sql)
                            else:
                                rows, err = [], "LLM did not generate SQL"
                            exec_ms = int((perf_counter() - t0) * 1000)
                            ses.set_attribute(
                                "f1.attrs",
                                __import__("json").dumps(
                                    {"row_count": len(rows), "error": err}
                                ),
                            )
                        sql_record = {
                            "generated_sql": gen_sql,
                            "cleaned_sql": cleaned,
                            "row_count": len(rows),
                            "execution_ms": exec_ms,
                            "timed_out": False,
                            "error": err,
                            "result_rows": rows[:50],
                            "gen_model": CHAT_MODEL,
                            "gen_tokens": u["total_tokens"],
                            "gen_latency_ms": gen_latency,
                        }

                # ---- merge ----
                merge_type = "orchestration" if route == "narrative" else "llm"
                with span("merger.merge", merge_type, route=route):
                    if route == "narrative":
                        final_answer = rag_answer
                    else:
                        chunks_for_prompt = (
                            [
                                {
                                    "text": c["text"],
                                    "title": c["title"],
                                    "source": c["source"],
                                }
                                for c in chunk_rows
                                if c["used_in_prompt"]
                            ]
                            if route == "both"
                            else []
                        )
                        m_msgs = merger_messages(
                            question=question,
                            sql_query=sql_record["generated_sql"]
                            if sql_record
                            else "",
                            sql_rows=sql_record["result_rows"]
                            if sql_record
                            else [],
                            chunks=chunks_for_prompt,
                        )
                        final_answer, u = chat_with_usage(m_msgs)
                        tot_prompt += u["prompt_tokens"]
                        tot_completion += u["completion_tokens"]
                        total_cost += cost.chat_cost(
                            CHAT_MODEL,
                            u["prompt_tokens"],
                            u["completion_tokens"],
                        )

                with span("guardrails.output", "guardrail") as os_:
                    ohits = run_output(question, final_answer, chunk_rows)
                    guardrails += ohits
                    os_.set_attribute(
                        "f1.attrs",
                        __import__("json").dumps(
                            {"triggered": [h["rule_name"] for h in ohits]}
                        ),
                    )
                if any(g["rule_name"] == "hallucination" for g in guardrails):
                    final_status = "flagged"

    latency_ms = int((perf_counter() - t_start) * 1000)

    rec: dict[str, Any] = {
        "request_id": request_id,
        "client_id": client_id,
        "session_id": session_id,
        "question": question,
        "final_answer": final_answer,
        "route": route_decision.get("category", "narrative"),
        "model": CHAT_MODEL,
        "prompt_version": prompt_version,
        "temperature": 0.2,
        "prompt_tokens": tot_prompt,
        "completion_tokens": tot_completion,
        "embedding_tokens": embed_tokens,
        "total_cost_usd": round(total_cost, 6),
        "latency_ms": latency_ms,
        "final_status": final_status,
        "replay_of_request_id": replay_of,
        "route_decision": route_decision
        or {
            "category": "narrative",
            "confidence": 0.0,
            "reasoning": "input refused",
            "router_model": CHAT_MODEL,
            "router_tokens": 0,
            "router_latency_ms": 0,
        },
        "chunks": chunk_rows,
        "sql_execution": sql_record,
        "spans": collector.rows(request_id),
        "guardrails": guardrails,
    }
    persist.save_trace(rec)
    return rec
