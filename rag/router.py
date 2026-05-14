"""Query router — classify question as structured / narrative / both.

Single LLM call with strict JSON schema output. Returns a RouteDecision
with category, confidence, and reasoning. The reasoning field will surface
as a Phase 4 span attribute and as the explanation shown to users when
the dashboard surfaces a route misclassification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from rag.llm import chat_json
from rag.prompts import ROUTER_SCHEMA, router_messages

Category = Literal["structured", "narrative", "both"]


@dataclass
class RouteDecision:
    category: Category
    confidence: float
    reasoning: str


def classify(question: str) -> RouteDecision:
    """One LLM call. Strict JSON output guaranteed by response_format=json_schema."""
    raw = chat_json(
        router_messages(question),
        schema=ROUTER_SCHEMA,
        schema_name="route_decision",
    )
    return RouteDecision(
        category=raw["category"],
        confidence=raw["confidence"],
        reasoning=raw["reasoning"],
    )
