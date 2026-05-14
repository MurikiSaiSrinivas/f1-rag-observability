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

## Observability architecture (locked 2026-05-14)

The full product architecture for the dashboard side of the project. Locked before Phase 2 begins so chunking captures the right metadata up-front and we don't pay the cost of a re-chunk/re-embed cycle later.

### Identity & access

- **No user accounts.** Each browser gets a UUID stored in cookie/localStorage as `client_id` on first visit.
- **Users see own history only** — backend filters by `client_id`.
- **Admin** is a separate role guarded by a hardcoded password in the `ADMIN_PASSWORD` env var; signed cookie after login. Single-tenant — one admin.
- **Accepted limitations:** cleared cookies → new identity; different devices → different identities. Fine for portfolio scope.

### Query routing & data sources

The system has **two backends for answering questions**, decided per request by a router:

- **Vector RAG** (Wikipedia + FIA chunks in Chroma) — answers narrative/explanatory questions: *"Explain the 2023 sporting regulations"*, *"Who is Lando Norris?"*, *"What happened at the 2021 Abu Dhabi GP?"*
- **SQL on Ergast** (SQLite) — answers structured-fact questions: *"How many wins did Verstappen have in 2023?"*, *"List all drivers who finished 2nd at Monaco 2020-2025"*

The **query router** (LLM call early in the pipeline) classifies each question into one of three modes:

- `structured` → SQL path only
- `narrative` → vector RAG path only
- `both` → both paths execute; an answer-merger LLM call combines results

**Why routed, not unified:** RAG over JSON tables fails on aggregation — the top-K retrieval limit can't surface all rows needed for counting (a corpus with 19 win-records can't be reliably counted by retrieving the top 5). SQL excels at exact counts/filters but is useless for narrative content. Routing each question to the right tool is the production-grade pattern.

**Each path is independently observable** — the dashboard shows the route decision, latency per path, and failure modes specific to each (retrieval misses, SQL generation errors, route misclassifications).

### Per-request data flow

Each `POST /ask` produces one trace, indexed by `request_id`:

1. **Capture request** — `request_id`, `client_id`, `session_id`, question, timestamp, model, prompt_version.
2. **Input guardrails** — off-topic, prompt-injection, PII detection, length checks. May abort.
3. **Query router** — LLM classifies question as `structured` / `narrative` / `both`; decision + confidence logged as a span.
4. **(narrative or both) Embed question** — OpenAI call; record tokens + latency.
5. **(narrative or both) Vector search in Chroma** — top-k chunks with similarity scores.
6. **(narrative or both) Retrieval guardrails** — low-similarity warning, empty-retrieval abort.
7. **(structured or both) Generate SQL** — LLM call with Ergast schema prompt → SQL string.
8. **(structured or both) Execute SQL** — run against `data/db/ergast.sqlite`; capture rows + query.
9. **Assemble context** — combine retrieved chunks and/or SQL result rows. Record which chunks made it into context vs. trimmed (retrieved-vs-used distinction).
10. **LLM synthesis** — final answer from combined context; tokens in/out, latency, cost.
11. **Output guardrails** — hallucination flag, PII-leak block, cost-spike flag.
12. **Return answer** to user, with the relevant guardrail reasons attached if any triggered.
13. **Async:** RAGAS scoring (faithfulness, relevance), flag rules.
14. **User feedback** — thumbs up/down + optional comment, attached to `request_id`.

### Data model (Phase 4 — Postgres)

| Table | Purpose |
|---|---|
| `clients` | Anonymous browser identities (UUID, first_seen_at, last_seen_at) |
| `sessions` | A conversation; many requests per session |
| `requests` | The central trace anchor: question, answer, model, prompt_version, tokens, cost, latency, final_status |
| `request_chunks` | Many-to-many: chunks retrieved per request, with rank, similarity, `used_in_prompt` flag |
| `chunks` | Materialized chunks with provenance metadata (mirror of `data/chunks/chunks.jsonl`) |
| `spans` | Per-step latency rows for the latency-breakdown view |
| `scores` | RAGAS metric rows per request |
| `flags` | Flag-rule outputs (incl. `sql_execution_error`, `sql_zero_results`, `route_misclassified`) |
| `sql_executions` | Per-request SQL: generated query, row count, execution time, error if any |
| `route_decisions` | Per-request router output: mode (`structured`/`narrative`/`both`), confidence, reasoning |
| `guardrails_triggered` | Which guardrails fired per request, with stage, action, severity, reason |
| `feedback` | Thumbs + comments per request |

### Chunk metadata schema (set at Phase 2)

Every chunk carries enough metadata to power all observability features downstream. Capturing this now avoids re-chunking + re-embedding later:

```json
{
  "chunk_id": "wikipedia/races/2023_bahrain_grand_prix#0007",
  "source": "wikipedia",
  "source_file_path": "data/raw/wikipedia/races/2023_bahrain_grand_prix.txt",
  "char_start": 4823,
  "char_end": 6210,
  "page_number": null,
  "text": "...",
  "title": "2023 Bahrain Grand Prix",
  "url": "https://en.wikipedia.org/wiki/2023_Bahrain_Grand_Prix",
  "metadata": {"season": 2023, "category": "races"}
}
```

- **Wikipedia chunks:** `source_file_path` is the `.txt`; `char_start`/`char_end` enable exact-text highlighting.
- **FIA chunks:** `source_file_path` is the **PDF** (not the `.txt`); `page_number` set; chunking runs on the extracted `.txt` but the dashboard renders the PDF.
- **Ergast data:** not chunked — served from a normalized SQLite database (`data/db/ergast.sqlite`) via the SQL pipeline. See "Query routing & data sources" above.

### Provenance UI

- **Wikipedia answers:** open the `.txt` in a content panel, highlight `char_start:char_end` in yellow for each contributing chunk.
- **FIA answers:** open the PDF in a PDF.js viewer; navigate to `page_number`; highlight chunk text via PDF.js's text-layer search (no coordinate math — works because regulation PDFs are single-column).
- **Ergast SQL answers:** show the **generated SQL query** + the **rows it returned** (table view). Provenance is the query and the data it pulled, not a highlighted source file.

### Guardrails

Hand-rolled rules for ~10 cases + **Guardrails AI** for one rule (`DetectPII`) — demonstrates fluency with both DIY rules and the standard library.

| Stage | Rule | Implementation | Effect |
|---|---|---|---|
| Input | `off_topic` | Hand-rolled (keyword + LLM fallback) | Refuse politely |
| Input | `prompt_injection` | Hand-rolled (pattern match) | Refuse |
| Input | `pii_in_question` | **Guardrails AI `DetectPII`** | Sanitize before logging |
| Input | `empty_or_too_short` | Hand-rolled | Reject |
| Input | `too_long` | Hand-rolled | Reject (cost guard) |
| Retrieval | `low_similarity` | Hand-rolled (threshold 0.5) | Continue, flag "no good sources" |
| Retrieval | `empty_retrieval` | Hand-rolled | Refuse to answer |
| Output | `hallucination` | Hand-rolled (RAGAS faithfulness < 0.7) | Show ⚠️ to user |
| Output | `refused_but_should_answer` | Hand-rolled | Flag for admin |
| Output | `pii_in_answer` | Hand-rolled (regex) | Block answer, fallback |
| Output | `excessive_cost` | Hand-rolled (per-request threshold) | Flag for admin |

All trigger reasons are shown in full to every user (option C — maximum transparency).

### Feature scope by role

| Feature | Users | Admin |
|---|---|---|
| Own question + answer history | ✅ | ✅ all users |
| Retrieved vs. used-in-prompt distinction | ✅ | ✅ |
| Replay past question with different prompt version | ✅ | ✅ |
| Thumbs up/down + optional comment | ✅ | ✅ |
| Full guardrail trigger reasons | ✅ | ✅ |
| Cost meter ($-spent today/week/month) | ❌ | ✅ |
| Latency breakdown per span | ❌ | ✅ |
| Bad Answers dashboard | ❌ | ✅ |
| Flag-rules dashboard | ❌ | ✅ |
| Per-user analytics | ❌ | ✅ |

## Full tech stack

### Storage
| Role | Tool | Phase | Status |
|---|---|---|---|
| Raw corpus | Filesystem + JSONL manifest | 1 | Locked |
| Vector store (Wikipedia + FIA chunks) | Chroma | 2 | Locked |
| Structured store (Ergast facts) | SQLite (file-based, no server) | 3 | Locked |
| App DB | Postgres | 4 | Locked |
| Span storage | TBD (Postgres vs Tempo / Jaeger / ClickHouse) | 4 | **Deferred decision** |

### Embedding model
- **Locked 2026-05-14:** OpenAI `text-embedding-3-small` ($0.02 / 1M tokens, hosted).
- Rationale: corpus is tiny (~2.25M tokens → ~$0.05 to embed), one API key covers embedding + Phase 3 LLM, and local `sentence-transformers` would add an 80-500MB model dependency without saving real money.

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
| 1 | LLM provider + model | 3 | OpenAI gpt-4o-mini vs Anthropic claude-haiku-4-5 |
| 2 | RAG framework | 3 | LangChain vs hand-rolled (concern: OTel tracing cleanliness) |
| 3 | Span storage backend | 4 | Postgres vs Tempo/Jaeger/ClickHouse (concern: convention) |

**Resolved:** Embedding model (OpenAI `text-embedding-3-small`, locked 2026-05-14).

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
| 1 | Data collection (Ergast/Jolpica, Wikipedia, FIA PDFs) | Done (2026-05-11) |
| 2 | Chunking, embedding, indexing (Chroma) | **Next** |
| 3 | Basic RAG pipeline + Ergast SQL pipeline + query router (deliberately not over-engineered) | Pending |
| 4 | Observability layer (architecture locked 2026-05-14 — see "Observability architecture" section) | Pending |
| 5 | Feedback loop demo (pick 3 real failures, fix, document before/after) | Pending |

### Phase 1 final corpus

- 531 documents total
- **Ergast/Jolpica**: 304 files (6,375 structured records across results, qualifying, standings, drivers, constructors, circuits, sprints) — 2020-2025, 131 races
- **Wikipedia**: 215 articles (131 races + 30 circuits + 40 drivers + 14 constructors), ~3.5M chars plaintext
- **FIA regulations**: 12 PDFs extracted to text (sporting + technical × 6 seasons), ~4.5M chars
- ~8M chars of natural-language corpus + structured JSON to enrich it
- All cataloged in `data/manifest.jsonl` (one row per source document)

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
