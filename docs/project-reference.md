# F1 RAG Observability — Project Reference

> Living reference for the project. Update as decisions are made and phases complete.

## Mission

This is an **observability project**, not a RAG project. The RAG pipeline is the workload being observed, not the deliverable. F1 was chosen as substrate for messy multi-source data and natural ambiguity (similar driver names, season-specific stats, team name changes, temporal confusion). The RAG is intentionally minimal and flawed so the observability layer has real failures to surface.

## Scope

- Seasons 2020-2025
- Race results, driver stats, constructor stats, race summaries, FIA regulations
- English text only
- No images, no telemetry, no real-time data

## Eight observability requirements

1. **Capture the request** — question, session ID, timestamp, model, prompt version, temperature, environment
2. **Trace the pipeline as spans** — router → retriever → chunks → LLM → tools → response (one trace end-to-end)
3. **Store retrieval context** — chunk IDs, similarity scores, source names
4. **Track system metrics** — latency, tokens, cost, error rate, retries
5. **Score answer quality** — faithfulness, relevance, hallucination, safety, cost, user feedback
6. **Flag bad answers** — no-source-but-confident, answer-contradicts-chunk, cost spike, prompt-version regression
7. **Bad Answers dashboard** — per flagged trace: question, chunks, answer, prompt version, model, cost, latency, faithfulness, feedback, failure reason
8. **Close the feedback loop** — trace → score → flag → debug → fix → retest

## Full tech stack

### Storage
| Role | Tool | Phase | Status |
|---|---|---|---|
| Raw corpus | Filesystem + JSONL manifest | 1 | Locked |
| Vector store | Chroma | 2 | Locked |
| App DB | Postgres | 4 | Locked |
| Span storage | TBD (Postgres vs Tempo / Jaeger / ClickHouse) | 4 | **Deferred decision** |

### Embedding model
- **Decision open before Phase 2.**
- Tentative pick: OpenAI `text-embedding-3-small` ($0.02 / 1M tokens, hosted).
- Alternative: local `sentence-transformers` (free, model download ~80-500MB).

### LLM
- **Decision open at Phase 3.**
- Tentative pick: OpenAI `gpt-4o-mini` ($0.15 / $0.60 per 1M tokens in/out).
- Alternative: Anthropic `claude-haiku-4-5` (~$1 / $5 per 1M tokens).

### RAG framework
- **Deferred decision at Phase 3.**
- Tentative: LangChain.
- Alternative: hand-rolled thin pipeline (LiteLLM or direct SDK + own retriever wrapper). Concern: LangChain's abstractions can fight clean OTel tracing.

### Backend service
- **FastAPI** — web framework; exposes `POST /ask` and admin endpoints for the dashboard
- **Pydantic** — schema validation (ships with FastAPI)
- **Uvicorn** — ASGI server

### Observability stack (the product)
- **OpenTelemetry** — industry-standard tracing protocol; every pipeline step is a span
- **RAGAS** — open-source RAG output scoring (faithfulness, relevance, etc.)
- Custom Python flagging module — reads spans + scores, applies flag rules

### Frontend (dashboard)
- **Next.js (React)** — framework
- **Tailwind CSS** — utility-first styling
- **shadcn/ui** — polished components on Radix + Tailwind
- **TanStack Query** — data fetching/caching against the FastAPI backend

### Dev / infra / glue
| Tool | Role | Phase |
|---|---|---|
| **uv** | Python package manager + venv (locked) | 1 |
| **httpx, tenacity, pypdf, tqdm** | HTTP client, retries, PDF parser, progress bars | 1 |
| **python-dotenv** | API key management via `.env` (kept out of git) | 2+ |
| **ruff** | Linter + formatter | 1 |
| **pytest** | Test framework | 2+ |
| **Docker + docker-compose** | Local Postgres + span backend (avoid polluting Windows install) | 4 |
| **GitHub Actions** | CI: lint + tests on push (visible badge on repo) | Throughout |
| **structlog** (optional) | Structured JSON logging | 4 |

## Open decisions

| # | Decision | Phase | Notes |
|---|---|---|---|
| 1 | Embedding model | Before 2 | OpenAI hosted vs local sentence-transformers |
| 2 | LLM provider + model | 3 | OpenAI gpt-4o-mini vs Anthropic claude-haiku-4-5 |
| 3 | RAG framework | 3 | LangChain vs hand-rolled (concern: OTel tracing cleanliness) |
| 4 | Span storage backend | 4 | Postgres vs Tempo/Jaeger/ClickHouse (concern: convention) |

## Deployment options

### Option A — Local only (free)
Everything runs via `docker-compose` on the dev machine. Demo via screen recording + strong README. **No live URL.** Cost: **$0**.

### Option B — Free-tier split (recommended for portfolio)
| Piece | Host | Cost |
|---|---|---|
| Next.js dashboard | Vercel (free tier) | $0 |
| FastAPI backend | Render or Fly.io | $0-5 |
| Postgres | Neon or Supabase (free tier) | $0 |
| Chroma | Self-hosted alongside backend | $0 |
| Span storage | Grafana Cloud free tier OR Postgres | $0 |
| **Total** | | **$0-5/mo** |

Gives you a live URL to put on your résumé. Big interview signal.

### Option C — Single VPS
DigitalOcean / Hetzner box running everything in Docker. More "real ops" feel; slightly more maintenance. **$5-12/mo**.

## Expected cost

### API spend (one-time, while building)
| Phase | Activity | Estimate |
|---|---|---|
| 1 | Data collection (free APIs — Ergast, Wikipedia, FIA) | $0 |
| 2 | Embedding ~5M tokens × $0.02/1M | ~$0.10 |
| 3 | RAG dev + testing (~500 queries) | ~$0.50 |
| 4 | Observability dev (~2000 queries incl. RAGAS scoring runs) | ~$6 |
| 5 | Demo runs | ~$1 |
| **Total to build everything end-to-end** | | **~$8-15** |

**Action item before Phase 2:** Set a **$20/mo hard spend cap** on the OpenAI dashboard. Both OpenAI and Anthropic support this.

### Subscription clarification (important)
- **Claude Max** and **ChatGPT Plus** are for the chat UIs (claude.ai, Claude Code, chatgpt.com). They do **NOT** include API credits.
- The deployed RAG app's LLM calls go through pay-per-use APIs and are billed separately, with their own credit card on file.
- Claude Max *does* cover Claude Code usage — i.e., the assistant building the project — but **not** the runtime app's calls.

## Phased plan

| Phase | Goal | Status |
|---|---|---|
| 0 | Scope lock | Done (2026-05-10) |
| 1 | Data collection (Ergast/Jolpica, Wikipedia, FIA PDFs) | **In progress** |
| 2 | Chunking, embedding, indexing (Chroma) | Pending |
| 3 | Basic RAG pipeline (deliberately not over-engineered) | Pending |
| 4 | Observability layer (the product — largest phase) | Pending |
| 5 | Feedback loop demo (pick 3 real failures, fix, document before/after) | Pending |

## Principles / rules

- **Observability is the product.** RAG is the workload being observed.
- **RAG stays minimal.** No reranking, hybrid search, or fancy retrieval until a real dashboard failure justifies it.
- **Improvements are data-driven**, not speculative.
- **Prefer standard primitives** (OpenTelemetry, RAGAS, uv) over custom solutions — interview-credibility lens.
- **Resist scope additions** in Phases 1-3. Polish there is premature.
- **Time push-back to the decision.** Don't preemptively litigate.

## Recommended first picks (subject to revisit at each phase)

- **Embedding:** OpenAI `text-embedding-3-small` (start hosted, switch to local only if it becomes a cost issue — it won't).
- **LLM:** OpenAI `gpt-4o-mini` (cheapest credible option; one API key covers both embedding and LLM).
- **Deployment target at Phase 5:** Option B (free-tier split) — Vercel + Render + Neon.
