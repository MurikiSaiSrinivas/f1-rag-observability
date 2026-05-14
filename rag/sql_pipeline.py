"""SQL pipeline — generate SQL via LLM and execute against the read-only Ergast DB.

Single public function: answer_structured(question) -> SqlResult.

Flow:
1. LLM call generates SQL given the schema doc baked into the prompt.
2. Execute against data/db/ergast.sqlite opened in read-only URI mode
   (?mode=ro) so any DDL/DML in hallucinated SQL fails harmlessly.
3. Return SqlResult with the SQL string, LLM's reasoning, rows as
   list[dict], and an optional error message.

Bounded: results truncated to ROW_CAP rows, SQLite has a query timeout.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rag.llm import chat_json
from rag.prompts import SQL_SCHEMA, sql_messages

DB_PATH = Path("data/db/ergast.sqlite")
RO_URI = f"file:{DB_PATH.as_posix()}?mode=ro"

# Hard caps so a weird LLM-generated query can't blow up cost or memory
ROW_CAP = 200
QUERY_TIMEOUT_S = 5

log = logging.getLogger("rag.sql_pipeline")


@dataclass
class SqlResult:
    """Output of the structured pipeline."""

    question: str
    sql: str                      # generated SQL string (may be empty if LLM refused)
    reasoning: str                # LLM's explanation of the SQL
    rows: list[dict[str, Any]]    # results as list of dicts, column-name keyed
    error: str | None = None      # sqlite3 error message; None on success
    row_count: int = 0


def _generate_sql(question: str) -> tuple[str, str]:
    """One LLM call. Returns (sql_string, reasoning). Strict JSON output."""
    raw = chat_json(
        sql_messages(question),
        schema=SQL_SCHEMA,
        schema_name="sql_query",
    )
    return raw["sql"], raw["reasoning"]


def _clean_sql(sql: str) -> str:
    """Normalize SQL string before execution.

    LLMs sometimes emit literal escape sequences (`\\n`, `\\t`, etc.) inside
    JSON-encoded SQL strings instead of real whitespace, which SQLite then
    rejects as unrecognized tokens. Replace them with spaces and trim.
    """
    return (
        sql.replace("\\n", " ")
        .replace("\\t", " ")
        .replace("\\r", " ")
        .strip()
    )


def _execute_sql(sql: str) -> tuple[list[dict[str, Any]], str | None]:
    """Run SQL against the read-only DB. Returns (rows, error_or_none).

    Connection uses URI mode with ?mode=ro so DDL/DML statements fail with
    'attempt to write a readonly database' instead of mutating state.
    """
    try:
        conn = sqlite3.connect(RO_URI, uri=True, timeout=QUERY_TIMEOUT_S)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(_clean_sql(sql))
            rows = cursor.fetchmany(ROW_CAP)
            return [dict(r) for r in rows], None
        finally:
            conn.close()
    except sqlite3.Error as e:
        return [], str(e)


def answer_structured(question: str) -> SqlResult:
    """Generate + execute SQL for a structured-fact question."""
    sql, reasoning = _generate_sql(question)

    if not sql.strip():
        return SqlResult(
            question=question,
            sql="",
            reasoning=reasoning,
            rows=[],
            error="LLM did not generate SQL (question may not fit this schema)",
            row_count=0,
        )

    rows, error = _execute_sql(sql)
    return SqlResult(
        question=question,
        sql=sql,
        reasoning=reasoning,
        rows=rows,
        error=error,
        row_count=len(rows),
    )
