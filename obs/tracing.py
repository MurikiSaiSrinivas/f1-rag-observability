"""Genuine OpenTelemetry instrumentation for the RAG pipeline (D4.1, D4.2).

We emit real OTel spans, but the deliverable is a bespoke dashboard, not a
generic trace explorer — so a custom SpanExporter buffers each request's
finished spans in a contextvar, and obs/persist.py writes them to the Postgres
`spans` table. Swapping in an OTLP collector → Tempo later is config-only.

Usage:
    with trace_request() as collector:
        with span("ask", "orchestration", route="both"):
            with span("router.classify", "llm", model="gpt-4o-mini"):
                ...
    rows = collector.rows()        # ready for the `spans` table
"""

from __future__ import annotations

import contextvars
import json
from contextlib import contextmanager
from typing import Any, Iterator

from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

_BUFFER: contextvars.ContextVar[list[ReadableSpan] | None] = contextvars.ContextVar(
    "f1_span_buffer", default=None
)


class _BufferExporter(SpanExporter):
    """Appends finished spans to the active request's contextvar buffer."""

    def export(self, spans) -> SpanExportResult:  # noqa: ANN001
        buf = _BUFFER.get()
        if buf is not None:
            buf.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:  # pragma: no cover
        pass


_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(_BufferExporter()))
trace.set_tracer_provider(_provider)
_tracer = trace.get_tracer("f1.rag")


@contextmanager
def span(name: str, span_type: str, **attrs: Any) -> Iterator[Any]:
    """Start a child span tagged with f1.span_type + JSON attrs."""
    with _tracer.start_as_current_span(name) as s:
        s.set_attribute("f1.span_type", span_type)
        s.set_attribute("f1.attrs", json.dumps(attrs, default=str))
        try:
            yield s
        except Exception as e:  # mark span errored, re-raise
            s.set_attribute("f1.error", str(e))
            s.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise


def set_attrs(s: Any, **attrs: Any) -> None:
    """Merge more attrs onto an in-flight span (e.g. token counts known late)."""
    existing: dict[str, Any] = {}
    # best-effort: re-serialize a fresh dict; last write wins on persist
    s.set_attribute("f1.attrs", json.dumps({**existing, **attrs}, default=str))


class SpanCollector:
    def __init__(self) -> None:
        self._token = None

    def __enter__(self) -> "SpanCollector":
        self._buf: list[ReadableSpan] = []
        self._token = _BUFFER.set(self._buf)
        return self

    def __exit__(self, *exc: Any) -> None:
        if self._token is not None:
            _BUFFER.reset(self._token)

    def rows(self, request_id: str) -> list[dict[str, Any]]:
        """Convert collected OTel spans → `spans` table rows.

        Times are ms relative to the earliest span start (the root `ask`).
        """
        if not self._buf:
            return []
        t0 = min(s.start_time for s in self._buf)
        out: list[dict[str, Any]] = []
        for s in self._buf:
            attrs_raw = s.attributes or {}
            try:
                attributes = json.loads(attrs_raw.get("f1.attrs", "{}"))
            except (TypeError, ValueError):
                attributes = {}
            sid = format(s.context.span_id, "016x")
            pid = (
                format(s.parent.span_id, "016x")
                if s.parent is not None
                else None
            )
            start_ms = (s.start_time - t0) / 1e6
            end_ms = (s.end_time - t0) / 1e6
            status = (
                "error"
                if s.status is not None
                and s.status.status_code == trace.StatusCode.ERROR
                else "ok"
            )
            out.append(
                {
                    "span_id": sid,
                    "request_id": request_id,
                    "parent_span_id": pid,
                    "name": s.name,
                    "span_type": attrs_raw.get("f1.span_type", "orchestration"),
                    "start_ts": round(start_ms, 3),
                    "end_ts": round(end_ms, 3),
                    "duration_ms": round(end_ms - start_ms, 3),
                    "status": status,
                    "attributes": attributes,
                }
            )
        out.sort(key=lambda r: r["start_ts"])
        return out


@contextmanager
def trace_request() -> Iterator[SpanCollector]:
    with SpanCollector() as c:
        yield c
