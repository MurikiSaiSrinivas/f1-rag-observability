"""Flagging module (4.6) — rules over the persisted request + scores + SQL.

Runs after scoring (RAGAS faithfulness is authoritative here, reconciling the
pre-RAGAS heuristic guardrail). Idempotent: clears this request's flags first,
so re-running scoring/flagging never duplicates.
"""

from __future__ import annotations

from obs import db

COST_CEILING = 0.004
FAITHFULNESS_TARGET = 0.85


def evaluate(request_id: str) -> None:
    r = db.fetchone(
        "SELECT route, final_answer, total_cost_usd, final_status "
        "FROM requests WHERE request_id=%s",
        (request_id,),
    )
    if not r:
        return

    faith = db.fetchone(
        "SELECT value FROM scores WHERE request_id=%s AND metric='faithfulness'",
        (request_id,),
    )
    sx = db.fetchone(
        "SELECT row_count, error FROM sql_executions WHERE request_id=%s",
        (request_id,),
    )
    sim = db.fetchone(
        "SELECT MAX(similarity) m FROM request_chunks WHERE request_id=%s",
        (request_id,),
    )
    best_sim = float(sim["m"]) if sim and sim["m"] is not None else None

    hits: list[tuple[str, str, str]] = []  # (name, description, severity)

    if (
        faith
        and faith["value"] < FAITHFULNESS_TARGET
        and r["route"] in ("narrative", "both")
    ):
        hits.append(
            (
                "hallucination",
                f"RAGAS faithfulness {faith['value']:.2f} below the "
                f"{FAITHFULNESS_TARGET} target.",
                "critical",
            )
        )

    if sx and not sx["error"] and sx["row_count"] == 0:
        hits.append(
            (
                "sql_zero_results",
                "Generated SQL executed successfully but returned 0 rows — "
                "likely a taxonomy/filter mismatch.",
                "warning",
            )
        )
        if r["route"] == "structured":
            hits.append(
                (
                    "route_misclassified",
                    "Routed structured but the DB had no rows — a narrative "
                    "answer may have served the user better.",
                    "warning",
                )
            )

    if (
        r["route"] in ("narrative", "both")
        and best_sim is not None
        and best_sim < 0.5
        and len(r["final_answer"]) > 200
    ):
        hits.append(
            (
                "no_source_but_confident",
                f"Substantial answer with no chunk above 0.5 "
                f"(best {best_sim:.2f}).",
                "critical",
            )
        )

    if float(r["total_cost_usd"]) > COST_CEILING:
        hits.append(
            (
                "cost_spike",
                f"Per-request cost ${float(r['total_cost_usd']):.4f} exceeds "
                f"the ${COST_CEILING} ceiling.",
                "info",
            )
        )

    db.execute("DELETE FROM flags WHERE request_id=%s", (request_id,))
    for name, desc, sev in hits:
        db.execute(
            "INSERT INTO flags (request_id, flag_name, description, severity) "
            "VALUES (%s,%s,%s,%s)",
            (request_id, name, desc, sev),
        )

    # reconcile request status with the authoritative flags
    new_status = r["final_status"]
    if any(h[0] == "hallucination" for h in hits):
        new_status = "flagged"
    elif hits and r["final_status"] == "success":
        new_status = "flagged"
    if new_status != r["final_status"]:
        db.execute(
            "UPDATE requests SET final_status=%s WHERE request_id=%s",
            (new_status, request_id),
        )
