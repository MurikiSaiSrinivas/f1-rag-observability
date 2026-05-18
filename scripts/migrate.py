"""Apply db/schema.sql to the observability Postgres database.

Idempotent — every statement is CREATE ... IF NOT EXISTS. Safe to re-run.

    uv run python scripts/migrate.py
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from obs.db import pool

SCHEMA = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


def main() -> int:
    load_dotenv()
    ddl = SCHEMA.read_text(encoding="utf-8")
    with pool().connection() as conn:
        conn.execute(ddl)
        # Prompt-version registry seed (D4.4) — replay + quality markers.
        for v, label, sp in [
            ("v1", "baseline", "Answer from the provided context."),
            (
                "v2",
                "stricter grounding",
                "Answer ONLY what the provided context supports; say so if it "
                "does not.",
            ),
        ]:
            conn.execute(
                "INSERT INTO prompt_versions (version, label, system_prompt) "
                "VALUES (%s,%s,%s) ON CONFLICT (version) DO NOTHING",
                (v, label, sp),
            )
    tables = [
        "clients",
        "sessions",
        "prompt_versions",
        "requests",
        "route_decisions",
        "chunks",
        "request_chunks",
        "sql_executions",
        "spans",
        "scores",
        "guardrails_triggered",
        "flags",
        "feedback",
    ]
    with pool().connection() as conn:
        for t in tables:
            n = conn.execute(
                f"SELECT count(*) FROM information_schema.tables "
                f"WHERE table_name = '{t}'"
            ).fetchone()
            print(f"  {t:<22} {'ok' if n and n[0] else 'MISSING'}")
    print("Schema applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
