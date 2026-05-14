"""Prompt templates for the routed RAG / SQL pipeline.

Plain Python — each helper returns a `messages` list ready for
openai.chat.completions, plus JSON schemas where the response is structured.
"""

from __future__ import annotations

from typing import Any

# ============================================================
# ROUTER — classify question as structured / narrative / both
# ============================================================

ROUTER_SYSTEM = """You are a query router for a Formula 1 question-answering system that has two data backends:

1. **SQL** — a normalized database of Ergast race data: drivers, constructors, races, race results, qualifying, sprint results, driver/constructor standings. Use when the question requires counts, aggregations, comparisons, specific finishing positions, lists, or exact factual data.

2. **RAG (vector search)** — Wikipedia race summaries, driver bios, constructor pages, circuit pages, and FIA regulation PDFs. Use when the question requires explanations, narrative context, regulatory interpretation, or descriptive content.

Classify each question into ONE category:
- "structured" — SQL alone can answer (e.g., "how many wins did X have?", "who finished 3rd at the 2023 Bahrain GP?", "list all drivers who won at Monaco").
- "narrative" — needs prose context (e.g., "explain what happened at Abu Dhabi 2021", "what is X known for?", "what do the regulations say about testing previous cars?").
- "both" — needs both hard facts AND prose context (e.g., "what happened at the 2021 Abu Dhabi GP and how did the season end?").

Respond in strict JSON. Prefer a single category when possible; use "both" only when both paths add real value."""


def router_messages(question: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": ROUTER_SYSTEM},
        {"role": "user", "content": f"Classify this question:\n\n{question}"},
    ]


ROUTER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": ["structured", "narrative", "both"],
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        },
        "reasoning": {
            "type": "string",
        },
    },
    "required": ["category", "confidence", "reasoning"],
    "additionalProperties": False,
}


# ============================================================
# RAG SYNTHESIS — answer from retrieved chunks (narrative path)
# ============================================================

RAG_SYSTEM = """You are an F1 expert answering questions using retrieved Wikipedia and FIA regulation excerpts.

RULES:
1. Answer based ONLY on the provided excerpts. Do not use outside knowledge.
2. If the excerpts do not contain the answer, say so plainly. Do not guess.
3. Cite each fact using [1], [2], etc., matching the chunk numbers.
4. Be concise. Prefer 1-3 sentences unless the question demands more detail.
5. If the question asks for a count or aggregate and the excerpts don't have a clear number, say "the excerpts don't contain a definitive count" rather than guessing."""


def rag_messages(question: str, chunks: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Build synthesis prompt with retrieved chunks numbered [1], [2], ..."""
    context_parts = []
    for i, c in enumerate(chunks, 1):
        title = c.get("title") or "(untitled)"
        source = c.get("source", "?")
        context_parts.append(f"[{i}] ({source}: {title})\n{c['text']}")
    context = "\n\n".join(context_parts) if context_parts else "(no excerpts retrieved)"

    return [
        {"role": "system", "content": RAG_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Question: {question}\n\n"
                f"Retrieved excerpts:\n\n{context}\n\n"
                f"Answer the question using only these excerpts. Cite sources with [1], [2], etc."
            ),
        },
    ]


# ============================================================
# SQL GENERATION — produce SQL from question + schema (structured path)
# ============================================================

SQL_SCHEMA_DOC = """The Ergast SQLite database has these tables (read-only):

drivers(driver_id PK, code, permanent_number, given_name, family_name, nationality, date_of_birth, wikipedia_url)
constructors(constructor_id PK, name, nationality, wikipedia_url)
circuits(circuit_id PK, circuit_name, locality, country, latitude, longitude, wikipedia_url)
races(season, round, race_name, date, time, circuit_id, wikipedia_url) -- PK (season, round)
race_results(season, round, driver_id, constructor_id, position, position_text, points, grid, laps, status, time_millis, fastest_lap_rank, fastest_lap_time) -- PK (season, round, driver_id)
qualifying_results(season, round, driver_id, constructor_id, position, q1, q2, q3) -- PK (season, round, driver_id)
sprint_results(season, round, driver_id, constructor_id, position, position_text, points, grid, laps, status, time_millis) -- PK (season, round, driver_id)
driver_standings(season, driver_id, position, position_text, points, wins, constructor_id) -- PK (season, driver_id)
constructor_standings(season, constructor_id, position, position_text, points, wins) -- PK (season, constructor_id)

IMPORTANT NOTES:
- driver_id is a slug: 'max_verstappen', 'hamilton', 'leclerc', 'norris', 'perez', etc.
- constructor_id is a slug: 'red_bull', 'mercedes', 'ferrari', 'mclaren', etc.
- circuit_id is a slug: 'monaco', 'bahrain', 'silverstone', 'spa', 'monza', etc.
- position is NULL when a driver retired; position_text is the literal ("1", "R", "D", "W"). Use position = 1 for race winners.
- status is free text: 'Finished', '+1 Lap', '+2 Laps', 'Accident', 'Engine', 'Brakes', 'Hydraulics', 'Collision', etc.
- Data covers seasons 2020-2025.
- driver_standings / constructor_standings hold end-of-season totals (precomputed by Ergast, accounts for half-points etc.).
"""


SQL_SYSTEM = f"""You are a SQL generator for the F1 Ergast SQLite database. Given a question, produce a SINGLE read-only SELECT query that answers it.

{SQL_SCHEMA_DOC}

RULES:
1. SELECT statements only. No INSERT/UPDATE/DELETE/DROP/ALTER (database is read-only and will reject them anyway).
2. Use the exact table/column names above. Slugs (driver_id, constructor_id, circuit_id) are lowercase.
3. Prefer COUNT(*), SUM(), AVG() when the question asks for aggregates.
4. JOIN on natural keys: races (season, round); per-race results (season, round, driver_id).
5. Use LIMIT 100 when listing rows, unless the question asks for fewer or all.
6. If the question can't be answered with these tables, return an empty sql string and explain in reasoning.

Respond with strict JSON: {{sql, reasoning}}."""


def sql_messages(question: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SQL_SYSTEM},
        {"role": "user", "content": f"Question: {question}"},
    ]


SQL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "sql": {
            "type": "string",
            "description": "A single read-only SELECT query, or empty string if the question can't be answered with this schema.",
        },
        "reasoning": {
            "type": "string",
            "description": "One or two sentences explaining the SQL approach.",
        },
    },
    "required": ["sql", "reasoning"],
    "additionalProperties": False,
}


# ============================================================
# ANSWER MERGER — combine SQL result + RAG chunks into one answer
# ============================================================

MERGER_SYSTEM = """You are an F1 expert combining structured data (from a SQL query) with narrative context (from Wikipedia/FIA excerpts) into one clear answer.

RULES:
1. Lead with the hard facts from the SQL result. They are authoritative.
2. Use narrative excerpts to add context, explanation, or color — never to overwrite SQL facts.
3. If SQL and narrative disagree on a number, trust SQL.
4. Be concise. Prefer 2-4 sentences unless the question demands more.
5. Cite narrative sources with [N1], [N2], etc., matching the chunk numbers."""


def merger_messages(
    question: str,
    sql_query: str,
    sql_rows: list[Any],
    chunks: list[dict[str, Any]],
) -> list[dict[str, str]]:
    sql_section = (
        f"SQL query:\n{sql_query}\n\n"
        f"SQL result ({len(sql_rows)} rows):\n{sql_rows}"
    )
    chunk_parts = []
    for i, c in enumerate(chunks, 1):
        title = c.get("title") or "(untitled)"
        source = c.get("source", "?")
        chunk_parts.append(f"[N{i}] ({source}: {title})\n{c['text']}")
    chunks_section = "\n\n".join(chunk_parts) if chunks else "(none)"

    return [
        {"role": "system", "content": MERGER_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Question: {question}\n\n"
                f"{sql_section}\n\n"
                f"Narrative excerpts:\n{chunks_section}\n\n"
                f"Combine these into one clear answer."
            ),
        },
    ]
