"""Postgres connection layer for the observability store (D4.1).

A lazily-created psycopg connection pool + thin sync helpers. Sync is fine at
portfolio scale; FastAPI runs route handlers in a threadpool. Every helper
returns dict rows so the API can hand them straight to Pydantic / JSON.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://f1obs:f1obs@localhost:5432/f1obs"
)

_pool: ConnectionPool | None = None


def pool() -> ConnectionPool:
    """Process-wide pool, opened on first use."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=8, open=True)
    return _pool


@contextmanager
def cursor() -> Iterator[Any]:
    """Dict-row cursor inside a transaction (commit on success, rollback on error)."""
    with pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            yield cur


def execute(sql: str, params: tuple | dict | None = None) -> None:
    with cursor() as cur:
        cur.execute(sql, params)


def fetchone(sql: str, params: tuple | dict | None = None) -> dict | None:
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def fetchall(sql: str, params: tuple | dict | None = None) -> list[dict]:
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def executemany(sql: str, rows: list[tuple]) -> None:
    if not rows:
        return
    with cursor() as cur:
        cur.executemany(sql, rows)
