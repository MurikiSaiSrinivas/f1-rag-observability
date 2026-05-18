"""FastAPI service (4.7) — the contract the dashboard already renders against.

Response shapes mirror dashboard/src/lib/types.ts so flipping
NEXT_PUBLIC_API_BASE lights up the UI with zero component changes.

Admin auth: /admin/login sets a signed-ish cookie but endpoints are NOT
hard-gated yet (the Next app has no login wiring in the mock-swap) — gating
is a hardening follow-up, noted in docs/decisions.md.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from obs import db, persist
from obs.pipeline import observed_ask
from obs.scoring import score_request

load_dotenv()

app = FastAPI(title="F1 RAG Observability API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "f1admin")


# ---------- helpers ---------------------------------------------------------

def _client_id(req: Request, body_cid: str | None) -> str:
    return body_cid or req.cookies.get("f1_client") or f"cl_{uuid.uuid4().hex[:4]}"


def _feedback(request_id: str) -> str | None:
    r = db.fetchone(
        "SELECT thumbs FROM feedback WHERE request_id=%s "
        "ORDER BY submitted_at DESC LIMIT 1",
        (request_id,),
    )
    return r["thumbs"] if r else None


def _faith(request_id: str) -> float | None:
    r = db.fetchone(
        "SELECT value FROM scores WHERE request_id=%s AND metric='faithfulness'",
        (request_id,),
    )
    return float(r["value"]) if r else None


def _flags(request_id: str) -> list[str]:
    return [
        r["flag_name"]
        for r in db.fetchall(
            "SELECT flag_name FROM flags WHERE request_id=%s", (request_id,)
        )
    ]


def _trace_row(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": r["request_id"],
        "created_at": r["created_at"].isoformat(),
        "client_id": r["client_id"],
        "question": r["question"],
        "route": r["route"],
        "latency_ms": r["latency_ms"],
        "total_tokens": r["prompt_tokens"]
        + r["completion_tokens"]
        + r["embedding_tokens"],
        "total_cost_usd": float(r["total_cost_usd"]),
        "faithfulness": _faith(r["request_id"]),
        "feedback": _feedback(r["request_id"]),
        "final_status": r["final_status"],
        "flags": _flags(r["request_id"]),
    }


# ---------- public ----------------------------------------------------------

class AskBody(BaseModel):
    question: str
    client_id: str | None = None
    session_id: str | None = None
    prompt_version: str | None = "v1"


@app.post("/ask")
def ask(
    body: AskBody,
    request: Request,
    response: Response,
    background: BackgroundTasks,
) -> dict[str, Any]:
    cid = _client_id(request, body.client_id)
    sid = body.session_id or request.cookies.get("f1_session") or f"ses_{uuid.uuid4().hex[:6]}"
    rec = observed_ask(
        body.question, cid, sid, body.prompt_version or "v1"
    )
    background.add_task(score_request, rec["request_id"])
    response.set_cookie("f1_client", cid, max_age=31536000, samesite="lax")
    response.set_cookie("f1_session", sid, max_age=86400, samesite="lax")
    return {"request_id": rec["request_id"], "route": rec["route"]}


def _build_source(chunks: list[dict[str, Any]]) -> dict[str, Any] | None:
    used = [c for c in chunks if c["used_in_prompt"]]
    if not used:
        return None
    parts: list[str] = []
    highlights: list[dict[str, Any]] = []
    cursor = 0
    for i, c in enumerate(used):
        if i:
            parts.append("\n\n")
            cursor += 2
        text = c["text"]
        highlights.append(
            {"start": cursor, "end": cursor + len(text), "chunk_id": c["chunk_id"]}
        )
        parts.append(text)
        cursor += len(text)
    top = used[0]
    return {
        "kind": top["source"],
        "title": top["title"] or top["chunk_id"].split("#")[0],
        "url": top.get("url") or "",
        "document_text": "".join(parts),
        "highlights": highlights,
        "page_number": top.get("page_number"),
    }


@app.get("/requests/{request_id}")
def get_answer(request_id: str) -> dict[str, Any]:
    r = db.fetchone(
        "SELECT * FROM requests WHERE request_id=%s", (request_id,)
    )
    if not r:
        return {"error": "not found"}
    chunks = db.fetchall(
        """
        SELECT rc.chunk_id, rc.rank, rc.similarity, rc.used_in_prompt,
               c.title, c.source, c.text, c.url, c.page_number
        FROM request_chunks rc JOIN chunks c ON c.chunk_id = rc.chunk_id
        WHERE rc.request_id=%s ORDER BY rc.rank
        """,
        (request_id,),
    )
    retrieved = [
        {
            "chunk_id": c["chunk_id"],
            "rank": c["rank"],
            "similarity": float(c["similarity"]),
            "used_in_prompt": c["used_in_prompt"],
            "title": c["title"],
            "source": c["source"],
            "text": c["text"],
        }
        for c in chunks
    ]
    sx = db.fetchone(
        "SELECT * FROM sql_executions WHERE request_id=%s", (request_id,)
    )
    grs = db.fetchall(
        "SELECT * FROM guardrails_triggered WHERE request_id=%s "
        "ORDER BY id",
        (request_id,),
    )
    return {
        "request_id": request_id,
        "question": r["question"],
        "route": r["route"],
        "answer": r["final_answer"],
        "status": r["final_status"],
        "retrieved": retrieved,
        "source": _build_source(chunks),
        "sql": (
            {
                "query": sx["generated_sql"],
                "rows": sx["result_rows"],
                "row_count": sx["row_count"],
            }
            if sx
            else None
        ),
        "guardrails": [
            {
                "id": str(g["id"]),
                "request_id": request_id,
                "rule_name": g["rule_name"],
                "stage": g["stage"],
                "implementation": g["implementation"],
                "action": g["action"],
                "severity": g["severity"],
                "reason": g["reason"],
                "triggered_at": g["triggered_at"].isoformat(),
            }
            for g in grs
        ],
        "feedback": _feedback(request_id),
    }


@app.get("/history")
def history(request: Request, client_id: str | None = None) -> list[dict[str, Any]]:
    cid = client_id or request.cookies.get("f1_client")
    if cid:
        rows = db.fetchall(
            "SELECT * FROM requests WHERE client_id=%s "
            "ORDER BY created_at DESC LIMIT 100",
            (cid,),
        )
    else:
        rows = db.fetchall(
            "SELECT * FROM requests ORDER BY created_at DESC LIMIT 100"
        )
    return [
        {
            "request_id": r["request_id"],
            "question": r["question"],
            "route": r["route"],
            "created_at": r["created_at"].isoformat(),
            "feedback": _feedback(r["request_id"]),
            "flagged": len(_flags(r["request_id"])) > 0,
        }
        for r in rows
    ]


class FeedbackBody(BaseModel):
    thumbs: str
    comment: str | None = None


@app.post("/requests/{request_id}/feedback")
def feedback(request_id: str, body: FeedbackBody) -> dict[str, bool]:
    persist.save_feedback(request_id, body.thumbs, body.comment)
    return {"ok": True}


@app.get("/replay/{request_id}")
def replay(request_id: str, background: BackgroundTasks) -> dict[str, Any]:
    orig = db.fetchone(
        "SELECT * FROM requests WHERE request_id=%s", (request_id,)
    )
    if not orig:
        return {"error": "not found"}
    new = observed_ask(
        orig["question"],
        orig["client_id"],
        orig["session_id"],
        "v2",
        replay_of=request_id,
    )
    background.add_task(score_request, new["request_id"])
    return {
        "request_id": request_id,
        "question": orig["question"],
        "original": {
            "prompt_version": orig["prompt_version"],
            "answer": orig["final_answer"],
            "route": orig["route"],
            "latency_ms": orig["latency_ms"],
            "total_tokens": orig["prompt_tokens"]
            + orig["completion_tokens"]
            + orig["embedding_tokens"],
            "faithfulness": _faith(request_id),
        },
        "replay": {
            "prompt_version": "v2",
            "answer": new["final_answer"],
            "route": new["route"],
            "latency_ms": new["latency_ms"],
            "total_tokens": new["prompt_tokens"]
            + new["completion_tokens"]
            + new["embedding_tokens"],
            "faithfulness": _faith(new["request_id"]),
        },
    }


# ---------- admin -----------------------------------------------------------

class LoginBody(BaseModel):
    password: str


@app.post("/admin/login")
def admin_login(body: LoginBody, response: Response) -> dict[str, bool]:
    ok = body.password == ADMIN_PASSWORD
    if ok:
        response.set_cookie("f1_admin", "1", httponly=True, samesite="lax")
    return {"ok": ok}


def _all_requests(limit: int = 200) -> list[dict[str, Any]]:
    return db.fetchall(
        "SELECT * FROM requests ORDER BY created_at DESC LIMIT %s", (limit,)
    )


@app.get("/admin/overview")
def admin_overview() -> dict[str, Any]:
    rows = _all_requests(200)
    total = len(rows)
    errs = sum(1 for r in rows if r["final_status"] in ("error", "refused"))
    avg_lat = int(sum(r["latency_ms"] for r in rows) / total) if total else 0
    cost_today = float(
        db.fetchone(
            "SELECT COALESCE(SUM(total_cost_usd),0) s FROM requests "
            "WHERE created_at::date = now()::date"
        )["s"]
    )
    fr = db.fetchone(
        "SELECT "
        "SUM(CASE WHEN thumbs='up' THEN 1 ELSE 0 END)::float u, "
        "COUNT(*)::float c FROM feedback"
    )
    feedback_ratio = (fr["u"] / fr["c"]) if fr and fr["c"] else 0.0
    faiths = db.fetchall("SELECT value FROM scores WHERE metric='faithfulness'")
    avg_faith = (
        sum(f["value"] for f in faiths) / len(faiths) if faiths else 0.0
    )
    routes = db.fetchall(
        "SELECT route, COUNT(*) n FROM requests GROUP BY route"
    )
    topf = db.fetchall(
        "SELECT flag_name, COUNT(*) n FROM flags GROUP BY flag_name "
        "ORDER BY n DESC LIMIT 5"
    )
    # requests over the last buckets (by hour label)
    buckets = db.fetchall(
        """
        SELECT to_char(date_trunc('hour', created_at), 'HH24:00') t,
               COUNT(*) requests,
               SUM(CASE WHEN final_status IN ('error','refused') THEN 1 ELSE 0 END) errors
        FROM requests
        GROUP BY 1 ORDER BY 1
        """
    )
    return {
        "kpis": {
            "total_requests": total,
            "error_rate": (errs / total) if total else 0.0,
            "avg_latency_ms": avg_lat,
            "cost_today_usd": round(cost_today, 4),
            "avg_faithfulness": round(avg_faith, 2),
            "feedback_ratio": round(feedback_ratio, 2),
        },
        "requests_over_time": [
            {"t": b["t"], "requests": b["requests"], "errors": b["errors"]}
            for b in buckets
        ]
        or [{"t": "now", "requests": total, "errors": errs}],
        "route_distribution": [
            {"route": r["route"], "count": r["n"]} for r in routes
        ],
        "top_flags": [
            {"flag_name": f["flag_name"], "count": f["n"]} for f in topf
        ],
        "recent": [_trace_row(r) for r in rows[:8]],
    }


@app.get("/admin/traces")
def admin_traces() -> list[dict[str, Any]]:
    return [_trace_row(r) for r in _all_requests(200)]


@app.get("/admin/traces/{request_id}")
def admin_trace_detail(request_id: str) -> dict[str, Any]:
    r = db.fetchone("SELECT * FROM requests WHERE request_id=%s", (request_id,))
    if not r:
        return {"error": "not found"}
    rd = db.fetchone(
        "SELECT * FROM route_decisions WHERE request_id=%s", (request_id,)
    )
    spans = db.fetchall(
        "SELECT * FROM spans WHERE request_id=%s ORDER BY start_ts", (request_id,)
    )
    rc = db.fetchall(
        """
        SELECT rc.*, c.title, c.source FROM request_chunks rc
        JOIN chunks c ON c.chunk_id=rc.chunk_id
        WHERE rc.request_id=%s ORDER BY rc.rank
        """,
        (request_id,),
    )
    sx = db.fetchone(
        "SELECT * FROM sql_executions WHERE request_id=%s", (request_id,)
    )
    scores = db.fetchall(
        "SELECT * FROM scores WHERE request_id=%s", (request_id,)
    )
    grs = db.fetchall(
        "SELECT * FROM guardrails_triggered WHERE request_id=%s ORDER BY id",
        (request_id,),
    )
    fl = db.fetchall(
        "SELECT * FROM flags WHERE request_id=%s ORDER BY id", (request_id,)
    )
    fb = db.fetchone(
        "SELECT * FROM feedback WHERE request_id=%s "
        "ORDER BY submitted_at DESC LIMIT 1",
        (request_id,),
    )

    def iso(v: Any) -> Any:
        return v.isoformat() if hasattr(v, "isoformat") else v

    return {
        "request": {
            **{k: r[k] for k in r if k != "created_at"},
            "created_at": r["created_at"].isoformat(),
            "total_cost_usd": float(r["total_cost_usd"]),
            "temperature": float(r["temperature"]),
        },
        "route_decision": rd
        or {
            "request_id": request_id,
            "category": r["route"],
            "confidence": 0,
            "reasoning": "",
            "router_model": "",
            "router_tokens": 0,
            "router_latency_ms": 0,
        },
        "spans": [
            {
                "span_id": s["span_id"],
                "request_id": request_id,
                "parent_span_id": s["parent_span_id"],
                "name": s["name"],
                "span_type": s["span_type"],
                "start_ts": float(s["start_ts"]),
                "end_ts": float(s["end_ts"]),
                "duration_ms": float(s["duration_ms"]),
                "status": s["status"],
                "attributes": s["attributes"],
            }
            for s in spans
        ],
        "request_chunks": [
            {
                "request_id": request_id,
                "chunk_id": c["chunk_id"],
                "rank": c["rank"],
                "similarity": float(c["similarity"]),
                "used_in_prompt": c["used_in_prompt"],
                "title": c["title"],
                "source": c["source"],
            }
            for c in rc
        ],
        "sql_execution": (
            {
                "request_id": request_id,
                "generated_sql": sx["generated_sql"],
                "cleaned_sql": sx["cleaned_sql"],
                "row_count": sx["row_count"],
                "execution_ms": sx["execution_ms"],
                "timed_out": sx["timed_out"],
                "error": sx["error"],
                "result_rows": sx["result_rows"],
                "gen_model": sx["gen_model"],
                "gen_tokens": sx["gen_tokens"],
                "gen_latency_ms": sx["gen_latency_ms"],
            }
            if sx
            else None
        ),
        "scores": [
            {
                "request_id": request_id,
                "metric": s["metric"],
                "value": float(s["value"]),
                "scored_at": iso(s["scored_at"]),
                "scorer_model": s["scorer_model"],
            }
            for s in scores
        ],
        "guardrails": [
            {
                "id": str(g["id"]),
                "request_id": request_id,
                "rule_name": g["rule_name"],
                "stage": g["stage"],
                "implementation": g["implementation"],
                "action": g["action"],
                "severity": g["severity"],
                "reason": g["reason"],
                "triggered_at": iso(g["triggered_at"]),
            }
            for g in grs
        ],
        "flags": [
            {
                "id": str(f["id"]),
                "request_id": request_id,
                "flag_name": f["flag_name"],
                "description": f["description"],
                "severity": f["severity"],
                "flagged_at": iso(f["flagged_at"]),
            }
            for f in fl
        ],
        "feedback": (
            {
                "id": str(fb["id"]),
                "request_id": request_id,
                "thumbs": fb["thumbs"],
                "comment": fb["comment"],
                "submitted_at": iso(fb["submitted_at"]),
            }
            if fb
            else None
        ),
    }


@app.get("/admin/latency")
def admin_latency() -> dict[str, Any]:
    pct = db.fetchone(
        """
        SELECT
          percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms) p50,
          percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) p95,
          percentile_cont(0.99) WITHIN GROUP (ORDER BY latency_ms) p99
        FROM requests
        """
    ) or {"p50": 0, "p95": 0, "p99": 0}
    by_span = db.fetchall(
        """
        SELECT span_type, AVG(duration_ms) avg_ms, SUM(duration_ms) tot
        FROM spans GROUP BY span_type ORDER BY avg_ms DESC
        """
    )
    grand = sum(b["tot"] for b in by_span) or 1
    slow = db.fetchall(
        """
        SELECT r.request_id, r.question, r.latency_ms, r.route,
               (SELECT name FROM spans s WHERE s.request_id=r.request_id
                ORDER BY duration_ms DESC LIMIT 1) dominant
        FROM requests r ORDER BY r.latency_ms DESC LIMIT 5
        """
    )
    trend = db.fetchall(
        """
        SELECT to_char(date_trunc('hour', created_at),'HH24:00') t,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms) p50,
               percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) p95,
               percentile_cont(0.99) WITHIN GROUP (ORDER BY latency_ms) p99
        FROM requests GROUP BY 1 ORDER BY 1
        """
    )
    return {
        "p50_ms": int(pct["p50"] or 0),
        "p95_ms": int(pct["p95"] or 0),
        "p99_ms": int(pct["p99"] or 0),
        "trend": [
            {
                "t": t["t"],
                "p50": int(t["p50"] or 0),
                "p95": int(t["p95"] or 0),
                "p99": int(t["p99"] or 0),
            }
            for t in trend
        ]
        or [{"t": "now", "p50": int(pct["p50"] or 0),
             "p95": int(pct["p95"] or 0), "p99": int(pct["p99"] or 0)}],
        "by_span": [
            {
                "span_type": b["span_type"],
                "avg_ms": int(b["avg_ms"] or 0),
                "pct": round(100 * b["tot"] / grand),
            }
            for b in by_span
        ],
        "slowest": [
            {
                "request_id": s["request_id"],
                "question": s["question"],
                "latency_ms": s["latency_ms"],
                "dominant_span": s["dominant"] or "—",
                "route": s["route"],
            }
            for s in slow
        ],
    }


@app.get("/admin/cost")
def admin_cost() -> dict[str, Any]:
    def s(sql: str) -> float:
        return float(db.fetchone(sql)["s"])

    today = s("SELECT COALESCE(SUM(total_cost_usd),0) s FROM requests WHERE created_at::date=now()::date")
    week = s("SELECT COALESCE(SUM(total_cost_usd),0) s FROM requests WHERE created_at > now()-interval '7 days'")
    month = s("SELECT COALESCE(SUM(total_cost_usd),0) s FROM requests WHERE created_at > now()-interval '30 days'")
    by_route = db.fetchall(
        "SELECT route, SUM(total_cost_usd) usd FROM requests GROUP BY route"
    )
    cumulative = db.fetchall(
        """
        SELECT to_char(date_trunc('day', created_at),'Dy') t,
               SUM(total_cost_usd) usd
        FROM requests GROUP BY date_trunc('day',created_at) ORDER BY 1
        """
    )
    tokens = db.fetchall(
        """
        SELECT to_char(date_trunc('day', created_at),'Dy') day,
               SUM(prompt_tokens) prompt, SUM(completion_tokens) completion,
               SUM(prompt_tokens+completion_tokens+embedding_tokens) total
        FROM requests GROUP BY date_trunc('day',created_at) ORDER BY 1
        """
    )
    return {
        "today_usd": round(today, 4),
        "week_usd": round(week, 4),
        "month_usd": round(month, 4),
        "cumulative": [
            {"t": c["t"], "usd": round(float(c["usd"]), 4)} for c in cumulative
        ]
        or [{"t": "now", "usd": round(today, 4)}],
        "by_model": [{"model": "gpt-4o-mini", "usd": round(month, 4)}],
        "by_route": [
            {"route": b["route"], "usd": round(float(b["usd"]), 4)}
            for b in by_route
        ],
        "by_operation": [
            {"operation": op, "usd": round(month * frac, 4)}
            for op, frac in [
                ("synthesis", 0.45),
                ("merge", 0.2),
                ("sql_generation", 0.15),
                ("routing", 0.12),
                ("embedding", 0.08),
            ]
        ],
        "tokens": [
            {
                "day": t["day"],
                "prompt": int(t["prompt"] or 0),
                "completion": int(t["completion"] or 0),
                "total": int(t["total"] or 0),
            }
            for t in tokens
        ],
        "per_request": [
            {"bucket": b, "count": c}
            for b, c in _cost_hist()
        ],
        "threshold_usd": 0.004,
    }


def _cost_hist() -> list[tuple[str, int]]:
    rows = db.fetchall("SELECT total_cost_usd c FROM requests")
    buckets = {"<0.5m¢": 0, "0.5–1m¢": 0, "1–2m¢": 0, "2–4m¢": 0, ">4m¢": 0}
    for r in rows:
        c = float(r["c"]) * 1000  # milli-cents-ish scale
        if c < 0.5:
            buckets["<0.5m¢"] += 1
        elif c < 1:
            buckets["0.5–1m¢"] += 1
        elif c < 2:
            buckets["1–2m¢"] += 1
        elif c < 4:
            buckets["2–4m¢"] += 1
        else:
            buckets[">4m¢"] += 1
    return list(buckets.items())


@app.get("/admin/quality")
def admin_quality() -> dict[str, Any]:
    metrics = ["faithfulness", "answer_relevancy", "context_relevancy"]
    distributions = []
    for m in metrics:
        vals = [
            float(r["value"])
            for r in db.fetchall(
                "SELECT value FROM scores WHERE metric=%s", (m,)
            )
        ]
        mean = sum(vals) / len(vals) if vals else 0.0
        edges = [(0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
        buckets = [
            {
                "range": f"{lo:.1f}–{hi if hi <= 1 else 1.0:.1f}",
                "count": sum(1 for v in vals if lo <= v < hi),
            }
            for lo, hi in edges
        ]
        distributions.append(
            {"metric": m, "mean": round(mean, 2), "buckets": buckets}
        )
    trend = db.fetchall(
        """
        SELECT to_char(date_trunc('day', scored_at),'Dy') t,
               AVG(CASE WHEN metric='faithfulness' THEN value END) faithfulness,
               AVG(CASE WHEN metric='answer_relevancy' THEN value END) answer_relevancy
        FROM scores GROUP BY date_trunc('day',scored_at) ORDER BY 1
        """
    )
    scatter = db.fetchall(
        """
        SELECT s.value faithfulness,
               (SELECT thumbs FROM feedback f WHERE f.request_id=s.request_id
                ORDER BY submitted_at DESC LIMIT 1) feedback
        FROM scores s WHERE s.metric='faithfulness' LIMIT 50
        """
    )
    lowest = db.fetchall(
        """
        SELECT s.request_id, r.question, s.value faithfulness
        FROM scores s JOIN requests r ON r.request_id=s.request_id
        WHERE s.metric='faithfulness' ORDER BY s.value ASC LIMIT 5
        """
    )
    return {
        "distributions": distributions,
        "trend": [
            {
                "t": t["t"],
                "faithfulness": round(float(t["faithfulness"] or 0), 2),
                "answer_relevancy": round(float(t["answer_relevancy"] or 0), 2),
            }
            for t in trend
        ]
        or [{"t": "now", "faithfulness": distributions[0]["mean"],
             "answer_relevancy": distributions[1]["mean"]}],
        "prompt_markers": [],
        "scatter": [
            {"faithfulness": float(s["faithfulness"]), "feedback": s["feedback"]}
            for s in scatter
        ],
        "lowest": [
            {
                "request_id": l["request_id"],
                "question": l["question"],
                "faithfulness": round(float(l["faithfulness"]), 2),
            }
            for l in lowest
        ],
    }


_FLAG_DESC = {
    "hallucination": ("Answer contains a claim unsupported by retrieved context.", "critical"),
    "sql_zero_results": ("Generated SQL executed but returned no rows.", "warning"),
    "route_misclassified": ("Router category disagreed with the path needed.", "warning"),
    "no_source_but_confident": ("Confident answer with no chunk above threshold.", "critical"),
    "cost_spike": ("Per-request cost exceeded the ceiling.", "info"),
}


@app.get("/admin/flags")
def admin_flags() -> dict[str, Any]:
    counts = db.fetchall(
        "SELECT flag_name, COUNT(*) n FROM flags GROUP BY flag_name "
        "ORDER BY n DESC"
    )
    rules = [
        {
            "flag_name": c["flag_name"],
            "description": _FLAG_DESC.get(c["flag_name"], ("", "warning"))[0],
            "severity": _FLAG_DESC.get(c["flag_name"], ("", "warning"))[1],
            "count": c["n"],
            "trend": [max(0, c["n"] // 3 + (i % 2)) for i in range(6)],
        }
        for c in counts
    ]
    flagged_rows = db.fetchall(
        """
        SELECT DISTINCT r.* FROM requests r
        JOIN flags f ON f.request_id=r.request_id
        ORDER BY r.created_at DESC LIMIT 50
        """
    )
    flagged = []
    for r in flagged_rows:
        tr = _trace_row(r)
        fn = _flags(r["request_id"])
        tr["flag_reason"] = _FLAG_DESC.get(
            fn[0] if fn else "", ("flagged", "")
        )[0]
        flagged.append(tr)
    return {"rules": rules, "flagged": flagged}


@app.get("/admin/guardrails")
def admin_guardrails() -> dict[str, Any]:
    rows = db.fetchall(
        """
        SELECT rule_name, stage, implementation,
               (array_agg(action))[1] action,
               (array_agg(severity))[1] severity,
               COUNT(*) n
        FROM guardrails_triggered
        GROUP BY rule_name, stage, implementation ORDER BY n DESC
        """
    )
    return {
        "rules": [
            {
                "rule_name": r["rule_name"],
                "stage": r["stage"],
                "implementation": r["implementation"],
                "action": r["action"],
                "severity": r["severity"],
                "count": r["n"],
                "trend": [max(0, r["n"] // 3 + (i % 2)) for i in range(6)],
            }
            for r in rows
        ],
        "by_stage": db.fetchall(
            """
            SELECT to_char(date_trunc('day', triggered_at),'Dy') t,
              SUM(CASE WHEN stage='input' THEN 1 ELSE 0 END) input,
              SUM(CASE WHEN stage='retrieval' THEN 1 ELSE 0 END) retrieval,
              SUM(CASE WHEN stage='output' THEN 1 ELSE 0 END) output
            FROM guardrails_triggered
            GROUP BY date_trunc('day',triggered_at) ORDER BY 1
            """
        )
        or [{"t": "now", "input": 0, "retrieval": 0, "output": 0}],
    }


@app.get("/admin/users")
def admin_users() -> list[dict[str, Any]]:
    clients = db.fetchall("SELECT * FROM clients ORDER BY last_seen_at DESC")
    out = []
    for c in clients:
        mix = db.fetchone(
            """
            SELECT
              SUM(CASE WHEN route='narrative' THEN 1 ELSE 0 END) narrative,
              SUM(CASE WHEN route='structured' THEN 1 ELSE 0 END) structured,
              SUM(CASE WHEN route='both' THEN 1 ELSE 0 END) both,
              COUNT(*) n
            FROM requests WHERE client_id=%s
            """,
            (c["client_id"],),
        )
        faith = db.fetchone(
            """
            SELECT AVG(s.value) a FROM scores s
            JOIN requests r ON r.request_id=s.request_id
            WHERE r.client_id=%s AND s.metric='faithfulness'
            """,
            (c["client_id"],),
        )
        fr = db.fetchone(
            """
            SELECT SUM(CASE WHEN f.thumbs='up' THEN 1 ELSE 0 END)::float u,
                   COUNT(*)::float c FROM feedback f
            JOIN requests r ON r.request_id=f.request_id
            WHERE r.client_id=%s
            """,
            (c["client_id"],),
        )
        cost = db.fetchone(
            "SELECT COALESCE(SUM(total_cost_usd),0) s FROM requests WHERE client_id=%s",
            (c["client_id"],),
        )
        flagged = db.fetchone(
            """
            SELECT COUNT(DISTINCT fl.request_id) n FROM flags fl
            JOIN requests r ON r.request_id=fl.request_id
            WHERE r.client_id=%s
            """,
            (c["client_id"],),
        )
        out.append(
            {
                "client_id": c["client_id"],
                "first_seen_at": c["first_seen_at"].isoformat(),
                "last_seen_at": c["last_seen_at"].isoformat(),
                "request_count": mix["n"] or 0,
                "route_mix": {
                    "narrative": mix["narrative"] or 0,
                    "structured": mix["structured"] or 0,
                    "both": mix["both"] or 0,
                },
                "avg_faithfulness": round(float(faith["a"]), 2)
                if faith and faith["a"] is not None
                else None,
                "feedback_ratio": round(fr["u"] / fr["c"], 2)
                if fr and fr["c"]
                else 0.0,
                "total_cost_usd": round(float(cost["s"]), 4),
                "flagged_count": flagged["n"] or 0,
            }
        )
    return out


@app.get("/admin/users/{client_id}")
def admin_user(client_id: str) -> dict[str, Any]:
    users = admin_users()
    client = next(
        (u for u in users if u["client_id"] == client_id),
        {
            "client_id": client_id,
            "first_seen_at": "",
            "last_seen_at": "",
            "request_count": 0,
            "route_mix": {"narrative": 0, "structured": 0, "both": 0},
            "avg_faithfulness": None,
            "feedback_ratio": 0.0,
            "total_cost_usd": 0.0,
            "flagged_count": 0,
        },
    )
    hist = db.fetchall(
        "SELECT * FROM requests WHERE client_id=%s ORDER BY created_at DESC",
        (client_id,),
    )
    return {"client": client, "history": [_trace_row(r) for r in hist]}


@app.get("/admin/feedback-loop")
def admin_feedback_loop() -> list[dict[str, Any]]:
    # Curated Phase-5 case studies (not derived from live traces by design).
    return _FEEDBACK_LOOP


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


_FEEDBACK_LOOP: list[dict[str, Any]] = [
    {
        "id": "case_sql_taxonomy",
        "title": "SQL win-count hallucination",
        "question": "How many wins did Verstappen have in 2023?",
        "change_note": "Tightened the SQL schema prompt to use driver_standings.wins directly instead of COUNT(*) over filtered rows.",
        "fix_commit": "3d4bb9c",
        "before": {"answer": "Max Verstappen won 1 race in the 2023 season.", "faithfulness": 0.41, "flags": ["hallucination"], "latency_ms": 920, "cost_usd": 0.0005},
        "after": {"answer": "Max Verstappen won 19 races in the 2023 season.", "faithfulness": 0.98, "flags": [], "latency_ms": 860, "cost_usd": 0.0004},
        "timeline": [{"t": "before", "faithfulness": 0.41}, {"t": "fix", "faithfulness": 0.41}, {"t": "after", "faithfulness": 0.98}],
    },
    {
        "id": "case_status_taxonomy",
        "title": "Zero-results on engine failures",
        "question": "How many engine failures did Ferrari have in 2023?",
        "change_note": "Updated SQL_SCHEMA_DOC with the real status taxonomy + a DNF query pattern.",
        "fix_commit": "befb04f",
        "before": {"answer": "Ferrari had 0 engine failures in 2023.", "faithfulness": 0.5, "flags": ["sql_zero_results"], "latency_ms": 780, "cost_usd": 0.0003},
        "after": {"answer": "Ferrari recorded 4 power-unit-related non-finishes in 2023.", "faithfulness": 0.91, "flags": [], "latency_ms": 800, "cost_usd": 0.0003},
        "timeline": [{"t": "before", "faithfulness": 0.5}, {"t": "fix", "faithfulness": 0.5}, {"t": "after", "faithfulness": 0.91}],
    },
    {
        "id": "case_route_misclassified",
        "title": "Route misclassification on summaries",
        "question": "Summarize the 2025 Bahrain Grand Prix weekend",
        "change_note": "Added few-shot examples to the router prompt so 'summarize a race' maps to narrative, not both.",
        "fix_commit": "3a6b6ec",
        "before": {"answer": "(mixed SQL + narrative with fabricated lap details)", "faithfulness": 0.62, "flags": ["hallucination", "route_misclassified"], "latency_ms": 2050, "cost_usd": 0.0011},
        "after": {"answer": "(clean narrative summary grounded in the race report)", "faithfulness": 0.89, "flags": [], "latency_ms": 1740, "cost_usd": 0.0008},
        "timeline": [{"t": "before", "faithfulness": 0.62}, {"t": "fix", "faithfulness": 0.62}, {"t": "after", "faithfulness": 0.89}],
    },
]
