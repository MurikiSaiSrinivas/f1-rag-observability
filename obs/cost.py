"""Token → USD cost. Tracked as if billed (the project runs on the free
OpenAI token-sharing program). Rates current as of 2026-05; cheap to update.
"""

from __future__ import annotations

# USD per 1M tokens
_RATES = {
    "gpt-4o-mini": {"in": 0.150, "out": 0.600},
    "gpt-4o": {"in": 2.50, "out": 10.0},
}
_EMBED_RATE = {"text-embedding-3-small": 0.020}


def chat_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    r = _RATES.get(model, _RATES["gpt-4o-mini"])
    return (prompt_tokens * r["in"] + completion_tokens * r["out"]) / 1_000_000


def embed_cost(model: str, tokens: int) -> float:
    rate = _EMBED_RATE.get(model, 0.020)
    return tokens * rate / 1_000_000
