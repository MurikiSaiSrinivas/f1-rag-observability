"""Write a completed trace to Postgres (D4.3).

Dependency order: client → session → request → route_decision →
chunks → request_chunks → sql_execution → spans. Guardrails/scores/flags are
written by their own modules (4.4–4.6).
"""

from __future__ import annotations

from typing import Any

from psycopg.types.json import Json

from obs import db


def ensure_client(client_id: str) -> None:
    db.execute(
        """
        INSERT INTO clients (client_id, first_seen_at, last_seen_at, request_count)
        VALUES (%s, now(), now(), 0)
        ON CONFLICT (client_id)
        DO UPDATE SET last_seen_at = now(),
                      request_count = clients.request_count + 1
        """,
        (client_id,),
    )


def ensure_session(session_id: str, client_id: str) -> None:
    db.execute(
        """
        INSERT INTO sessions (session_id, client_id, started_at, last_activity_at)
        VALUES (%s, %s, now(), now())
        ON CONFLICT (session_id)
        DO UPDATE SET last_activity_at = now()
        """,
        (session_id, client_id),
    )


def save_trace(rec: dict[str, Any]) -> None:
    """Persist one /ask trace. `rec` is the dict built by obs.pipeline."""
    ensure_client(rec["client_id"])
    ensure_session(rec["session_id"], rec["client_id"])

    db.execute(
        """
        INSERT INTO requests (
          request_id, client_id, session_id, question, final_answer, route,
          model, prompt_version, temperature, prompt_tokens, completion_tokens,
          embedding_tokens, total_cost_usd, latency_ms, final_status,
          replay_of_request_id
        ) VALUES (
          %(request_id)s, %(client_id)s, %(session_id)s, %(question)s,
          %(final_answer)s, %(route)s, %(model)s, %(prompt_version)s,
          %(temperature)s, %(prompt_tokens)s, %(completion_tokens)s,
          %(embedding_tokens)s, %(total_cost_usd)s, %(latency_ms)s,
          %(final_status)s, %(replay_of_request_id)s
        )
        """,
        rec,
    )

    rd = rec["route_decision"]
    db.execute(
        """
        INSERT INTO route_decisions (
          request_id, category, confidence, reasoning, router_model,
          router_tokens, router_latency_ms
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            rec["request_id"],
            rd["category"],
            rd["confidence"],
            rd["reasoning"],
            rd["router_model"],
            rd["router_tokens"],
            rd["router_latency_ms"],
        ),
    )

    for c in rec.get("chunks", []):
        db.execute(
            """
            INSERT INTO chunks (
              chunk_id, source, source_file_path, char_start, char_end,
              page_number, title, url, text, metadata
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (chunk_id) DO NOTHING
            """,
            (
                c["chunk_id"],
                c["source"],
                c["source_file_path"],
                c["char_start"],
                c["char_end"],
                c["page_number"],
                c["title"],
                c["url"],
                c["text"],
                Json(c["metadata"]),
            ),
        )
        db.execute(
            """
            INSERT INTO request_chunks (
              request_id, chunk_id, rank, similarity, used_in_prompt
            ) VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (request_id, chunk_id) DO NOTHING
            """,
            (
                rec["request_id"],
                c["chunk_id"],
                c["rank"],
                c["similarity"],
                c["used_in_prompt"],
            ),
        )

    sx = rec.get("sql_execution")
    if sx is not None:
        db.execute(
            """
            INSERT INTO sql_executions (
              request_id, generated_sql, cleaned_sql, row_count, execution_ms,
              timed_out, error, result_rows, gen_model, gen_tokens,
              gen_latency_ms
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                rec["request_id"],
                sx["generated_sql"],
                sx["cleaned_sql"],
                sx["row_count"],
                sx["execution_ms"],
                sx["timed_out"],
                sx["error"],
                Json(sx["result_rows"]),
                sx["gen_model"],
                sx["gen_tokens"],
                sx["gen_latency_ms"],
            ),
        )

    for s in rec.get("spans", []):
        db.execute(
            """
            INSERT INTO spans (
              span_id, request_id, parent_span_id, name, span_type,
              start_ts, end_ts, duration_ms, status, attributes
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (span_id) DO NOTHING
            """,
            (
                s["span_id"],
                s["request_id"],
                s["parent_span_id"],
                s["name"],
                s["span_type"],
                s["start_ts"],
                s["end_ts"],
                s["duration_ms"],
                s["status"],
                Json(s["attributes"]),
            ),
        )

    for g in rec.get("guardrails", []):
        db.execute(
            """
            INSERT INTO guardrails_triggered (
              request_id, rule_name, stage, implementation, action, severity,
              reason
            ) VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                rec["request_id"],
                g["rule_name"],
                g["stage"],
                g["implementation"],
                g["action"],
                g["severity"],
                g["reason"],
            ),
        )


def save_feedback(request_id: str, thumbs: str, comment: str | None) -> None:
    db.execute(
        """
        INSERT INTO feedback (request_id, thumbs, comment)
        VALUES (%s, %s, %s)
        """,
        (request_id, thumbs, comment),
    )


def save_scores(request_id: str, scores: list[dict[str, Any]]) -> None:
    for s in scores:
        db.execute(
            """
            INSERT INTO scores (request_id, metric, value, scorer_model)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (request_id, metric)
            DO UPDATE SET value = EXCLUDED.value, scored_at = now()
            """,
            (request_id, s["metric"], s["value"], s.get("scorer_model", "")),
        )


def save_flags(request_id: str, flags: list[dict[str, Any]]) -> None:
    for f in flags:
        db.execute(
            """
            INSERT INTO flags (request_id, flag_name, description, severity)
            VALUES (%s,%s,%s,%s)
            """,
            (request_id, f["flag_name"], f["description"], f["severity"]),
        )
