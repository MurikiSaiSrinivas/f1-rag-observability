"""OpenAI chat completions wrapper — plain text + structured JSON variants.

Two public functions:
- chat() returns plain text (for synthesis prompts).
- chat_json() returns parsed JSON, constrained by a JSON Schema (for the
  router and SQL generator, where structure matters).

Both share a single module-level OpenAI client for efficiency across calls.
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

CHAT_MODEL = "gpt-4o-mini"

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def chat(
    messages: list[dict[str, str]],
    *,
    model: str = CHAT_MODEL,
    temperature: float = 0.2,
    max_tokens: int = 1500,
) -> str:
    """Plain-text chat completion. Used for narrative synthesis and answer merging."""
    response = _get_client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


def chat_json(
    messages: list[dict[str, str]],
    *,
    schema: dict[str, Any],
    schema_name: str,
    model: str = CHAT_MODEL,
    temperature: float = 0.0,
    max_tokens: int = 800,
) -> dict[str, Any]:
    """Chat completion with strict JSON schema output.

    Uses OpenAI's structured-outputs feature: the model is constrained to
    produce JSON exactly matching `schema`. Eliminates a whole class of
    parsing failures vs. asking nicely in the prompt.

    Used by the router (returns route_decision) and the SQL generator (returns
    sql + reasoning).
    """
    response = _get_client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": schema,
            },
        },
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)
