# F1 RAG Observability

An observability layer wrapped around a deliberately-minimal F1 RAG pipeline. Traces, scores, flags, and debugs bad answers — production-style AI observability built end-to-end.

The RAG is the *workload being observed*, not the deliverable. F1 was chosen as substrate for its messy, multi-source public data and natural ambiguity, so failures are realistic and visible in the dashboard.

## Stack

Python + FastAPI · Chroma (vectors) · Postgres (app DB) · OpenTelemetry (tracing) · RAGAS (quality scoring) · Next.js + Tailwind + shadcn (dashboard).

## Setup

```bash
uv sync                  # install dependencies
cp .env.example .env     # copy env template; fill in your API keys
```

## Documentation

- [`docs/project-reference.md`](docs/project-reference.md) — tech stack, costs, deployment, phased plan
- [`docs/project-structure.md`](docs/project-structure.md) — repo layout and design decisions

## Status

Phase 1 (data collection) — in progress.
