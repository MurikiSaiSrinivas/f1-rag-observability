"""Guardrails (4.4) — hand-rolled rules across input / retrieval / output.

Each rule returns a "hit" dict when it fires:
  {rule_name, stage, implementation, action, severity, reason}

Architecture note / deferred sub-decision: the locked design wants ONE rule
(`pii_in_question`) powered by the Guardrails AI library to demonstrate both
DIY and library approaches. Guardrails AI pulls Presidio + spaCy models —
heavy and fragile to install on this Python/OS, and not worth risking the
whole backend mid-build. It's implemented hand-rolled here behind the SAME
`run_input` seam; swapping in `guardrails.hub.DetectPII` later is a
one-function change (see `_pii_match`). Tracked in docs/decisions.md.
"""

from __future__ import annotations

import re
from typing import Any

Hit = dict[str, Any]

_INJECTION = re.compile(
    r"\b(ignore (all |the )?(previous|prior) instructions|disregard (the|all) "
    r"above|system prompt|reveal your (system )?prompt|you are now|act as)\b",
    re.I,
)
_OFF_TOPIC = re.compile(
    r"\b(recipe|weather|stock price|bitcoin|horoscope|medical advice|"
    r"who are you|write code|essay about)\b",
    re.I,
)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CC = re.compile(r"\b(?:\d[ -]*?){13,16}\b")


def _hit(name, stage, impl, action, severity, reason) -> Hit:  # noqa: ANN001
    return {
        "rule_name": name,
        "stage": stage,
        "implementation": impl,
        "action": action,
        "severity": severity,
        "reason": reason,
    }


def _pii_match(text: str) -> str | None:
    """PII detector. Hand-rolled regex today; the Guardrails AI `DetectPII`
    validator drops in here behind the same return contract."""
    if _EMAIL.search(text):
        return "email address"
    if _SSN.search(text):
        return "national ID number"
    if _CC.search(text) and len(re.sub(r"\D", "", text)) >= 13:
        return "card-like number"
    if _PHONE.search(text):
        return "phone number"
    return None


def run_input(question: str) -> list[Hit]:
    hits: list[Hit] = []
    q = question.strip()
    if len(q) < 4 or len(q.split()) < 2:
        hits.append(
            _hit(
                "empty_or_too_short",
                "input",
                "hand_rolled",
                "reject",
                "info",
                "Question is empty or too short to answer.",
            )
        )
    if len(q) > 1000:
        hits.append(
            _hit(
                "too_long",
                "input",
                "hand_rolled",
                "reject",
                "info",
                f"Question is {len(q)} chars (>1000) — rejected as a cost guard.",
            )
        )
    if _INJECTION.search(q):
        hits.append(
            _hit(
                "prompt_injection",
                "input",
                "hand_rolled",
                "refuse",
                "critical",
                "Input matches a prompt-injection pattern.",
            )
        )
    if _OFF_TOPIC.search(q):
        hits.append(
            _hit(
                "off_topic",
                "input",
                "hand_rolled",
                "refuse",
                "info",
                "Question appears unrelated to Formula 1 (2020–2025).",
            )
        )
    pii = _pii_match(q)
    if pii:
        hits.append(
            _hit(
                "pii_in_question",
                "input",
                "hand_rolled",  # Guardrails AI DetectPII swaps in here
                "sanitize",
                "warning",
                f"Possible {pii} detected in the question; sanitized before logging.",
            )
        )
    return hits


def run_retrieval(chunk_rows: list[dict[str, Any]]) -> list[Hit]:
    hits: list[Hit] = []
    if not chunk_rows:
        hits.append(
            _hit(
                "empty_retrieval",
                "retrieval",
                "hand_rolled",
                "refuse",
                "warning",
                "No chunks retrieved for this question.",
            )
        )
        return hits
    best = max(c["similarity"] for c in chunk_rows)
    if best < 0.5:
        hits.append(
            _hit(
                "low_similarity",
                "retrieval",
                "hand_rolled",
                "warn",
                "warning",
                f"Top retrieval similarity {best:.2f} is below the 0.5 "
                f"threshold — sources may be weak.",
            )
        )
    return hits


def run_output(
    question: str, answer: str, chunk_rows: list[dict[str, Any]]
) -> list[Hit]:
    hits: list[Hit] = []
    pii = _pii_match(answer)
    if pii:
        hits.append(
            _hit(
                "pii_in_answer",
                "output",
                "hand_rolled",
                "block",
                "critical",
                f"Possible {pii} detected in the answer; blocked.",
            )
        )
    # Heuristic hallucination signal pre-RAGAS: a confident, substantial answer
    # built on weak retrieval. RAGAS faithfulness (4.5) is authoritative and
    # reconciled by the flagging module (4.6).
    if chunk_rows:
        best = max(c["similarity"] for c in chunk_rows)
        if best < 0.5 and len(answer) > 200:
            hits.append(
                _hit(
                    "hallucination",
                    "output",
                    "hand_rolled",
                    "warn",
                    "critical",
                    f"Substantial answer grounded only in low-similarity "
                    f"chunks (best {best:.2f}).",
                )
            )
    return hits
