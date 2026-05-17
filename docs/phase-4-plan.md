# Phase 4 — Observability Layer: Plan + Data/API Contract

> The deliverable phase. RAG + SQL pipeline (Phases 1–3) is the workload; this
> phase is the product. Architecture was locked 2026-05-14 — see
> `docs/project-reference.md` → "Observability architecture". This document is
> the **plan** and the **contract** the Stitch screens render against. It is
> planning/spec only — no implementation code is written until each step is
> signed off.

---

## 0. The one open decision (due now)

Everything else here is locked. One decision was deliberately deferred to
"Phase 4 start" — and we're there: **where do OpenTelemetry spans get stored?**

| Option | What it is | Cost for this project |
|---|---|---|
| **A. Postgres only (recommended)** | Emit real OTel spans, export via a custom span processor into the Postgres `spans` table | One datastore, zero extra infra, SQL-queryable for the latency screens |
| B. Jaeger | Classic OTel trace backend with its own UI | Extra service; its UI **competes** with the custom Trace Detail screen we're building |
| C. Tempo + Grafana | Object-storage traces + Grafana | Heavy infra, overkill at portfolio scale |
| D. ClickHouse | Columnar store for high-volume trace analytics | Massive overkill for a few thousand requests |

**Recommendation: A.** Still instrument with genuine OpenTelemetry (the
interview-credible part), but persist spans in Postgres because the deliverable
is a *bespoke* observability UI, not a generic trace explorer — Jaeger/Tempo
would just duplicate the dashboard we're hand-building. Infra stays at one
Postgres container. The interview story is strong and defensible: *"I
instrumented with OpenTelemetry and persist spans in Postgres because the
product is a custom UI; swapping to an OTLP collector → Tempo is a config
change, noted in the code."* This also matches the project thesis (observability
*over* RAG, hand-rolled for clean span control — decision D3.2).

**✅ Resolved 2026-05-17 — Option A chosen** (logged as D4.1 in
`docs/decisions.md`). The data model below assumes A.

---

## 1. Scope recap — the 8 requirements → where each lives

| # | Requirement | Delivered by |
|---|---|---|
| 1 | Capture the request | `requests` row + root span (step 4.3) |
| 2 | Trace pipeline as spans | OTel instrumentation (step 4.2) → Trace Detail screen |
| 3 | Store retrieval context | `request_chunks` + `chunks` (step 4.3) |
| 4 | Track system metrics | `spans`, latency/cost endpoints (steps 4.2, 4.7) |
| 5 | Score answer quality | RAGAS module → `scores` (step 4.5) |
| 6 | Flag bad answers | Flag module → `flags` (step 4.6) |
| 7 | Bad Answers dashboard | `/admin/flags` endpoint + Screen 12 |
| 8 | Close the feedback loop | Replay + before/after (steps 4.8, Phase 5) |

---

## 2. Data model contract (Postgres, 12 tables)

Field-level contract the screens and backend share. Types are conceptual; the
SQL DDL is the build artifact of step 4.1.

### `clients` — anonymous browser identities
`client_id` (UUID, PK) · `first_seen_at` · `last_seen_at` · `request_count`

### `sessions` — a conversation (many requests per session)
`session_id` (UUID, PK) · `client_id` (FK→clients) · `started_at` · `last_activity_at`

### `requests` — central trace anchor (one row per /ask)
`request_id` (UUID, PK) · `client_id` (FK) · `session_id` (FK) · `question` ·
`final_answer` · `route` (`narrative`/`structured`/`both`) · `model` ·
`prompt_version` · `temperature` · `prompt_tokens` · `completion_tokens` ·
`embedding_tokens` · `total_cost_usd` · `latency_ms` · `final_status`
(`success`/`error`/`refused`/`flagged`) · `created_at` · `replay_of_request_id`
(nullable FK→requests, for replays)

### `route_decisions` — router output per request
`request_id` (FK, PK) · `category` · `confidence` · `reasoning` ·
`router_model` · `router_tokens` · `router_latency_ms`

### `chunks` — materialized chunk corpus (mirror of `data/chunks/chunks.jsonl`)
`chunk_id` (PK) · `source` (`wikipedia`/`fia`) · `source_file_path` ·
`char_start` · `char_end` · `page_number` (FIA only) · `title` · `url` ·
`text` · `metadata` (JSONB: season/category or doc_type)

### `request_chunks` — retrieved-vs-used (many-to-many)
`request_id` (FK) · `chunk_id` (FK) · `rank` · `similarity` ·
`used_in_prompt` (bool) — PK (`request_id`, `chunk_id`)

### `sql_executions` — SQL path per request
`request_id` (FK, PK) · `generated_sql` · `cleaned_sql` · `row_count` ·
`execution_ms` · `timed_out` (bool) · `error` (nullable) · `result_rows`
(JSONB, capped) · `gen_model` · `gen_tokens` · `gen_latency_ms`

### `spans` — per-step trace rows (the waterfall)
`span_id` (PK) · `request_id` (FK) · `parent_span_id` (nullable) · `name` ·
`span_type` · `start_ts` · `end_ts` · `duration_ms` · `status`
(`ok`/`error`) · `attributes` (JSONB: tokens, cost, model, inputs/outputs,
chunk_ids, sql, etc.) — see span taxonomy §3

### `scores` — RAGAS metrics per request
`request_id` (FK) · `metric` (`faithfulness`/`answer_relevancy`/
`context_relevancy`) · `value` (0–1) · `scored_at` · `scorer_model` —
PK (`request_id`, `metric`)

### `guardrails_triggered` — every guardrail that fired
`id` (PK) · `request_id` (FK) · `rule_name` · `stage`
(`input`/`retrieval`/`output`) · `implementation` (`hand_rolled`/
`guardrails_ai`) · `action` (`refuse`/`reject`/`sanitize`/`flag`/`block`/
`warn`) · `severity` (`info`/`warning`/`critical`) · `reason` ·
`triggered_at`

### `flags` — flag-rule outputs (async)
`id` (PK) · `request_id` (FK) · `flag_name` · `description` · `severity` ·
`flagged_at` — flag names include `no_source_but_confident`,
`answer_contradicts_chunk`, `cost_spike`, `prompt_version_regression`,
`sql_execution_error`, `sql_zero_results`, `route_misclassified`,
`hallucination`

### `feedback` — thumbs + comment per request
`id` (PK) · `request_id` (FK) · `thumbs` (`up`/`down`) · `comment`
(nullable) · `submitted_at`

---

## 3. OpenTelemetry span taxonomy (the trace contract)

One trace per `/ask`. Span names, parent, and attributes are fixed here so the
Trace Detail waterfall (Screen 8) and the latency screens render consistently.

```
ask                              (ROOT)  attrs: request_id, client_id,
│                                        session_id, question, route,
│                                        prompt_version, model, final_status,
│                                        total latency/tokens/cost
├─ guardrails.input              attrs: rules_checked[], triggered[], action,
│                                        aborted(bool)
├─ router.classify               attrs: category, confidence, reasoning,
│                                        model, tokens, cost, latency_ms
├─ rag.pipeline                  (only if route ∈ {narrative, both})
│  ├─ rag.embed_query            attrs: model, embedding_tokens, latency_ms
│  ├─ rag.vector_search          attrs: top_k, returned_chunk_ids[],
│  │                                    similarities[], latency_ms
│  ├─ guardrails.retrieval       attrs: triggered[] (low_similarity,
│  │                                    empty_retrieval), action
│  └─ rag.synthesis              attrs: model, prompt_tokens,
│                                       completion_tokens, cost,
│                                       used_chunk_ids[], latency_ms
├─ sql.pipeline                  (only if route ∈ {structured, both})
│  ├─ sql.generate               attrs: model, tokens, cost,
│  │                                    generated_sql, latency_ms
│  └─ sql.execute                attrs: cleaned_sql, row_count,
│                                       execution_ms, timed_out, error
├─ merger.merge                  attrs: route, llm_called(bool), model,
│                                        tokens, cost, latency_ms
└─ guardrails.output             attrs: triggered[] (hallucination,
                                         pii_in_answer, excessive_cost,
                                         refused_but_should_answer), action

ASYNC (linked trace, not blocking the response):
scoring.ragas                    attrs: faithfulness, answer_relevancy,
                                         context_relevancy, scorer_model
flags.evaluate                   attrs: flags_fired[]
```

`span_type` color key for the waterfall: `guardrail` (amber), `llm` (red),
`retrieval` (blue), `sql` (green), `orchestration` (grey).

---

## 4. API contract (FastAPI)

Identity: public requests carry `client_id` (cookie/localStorage UUID; created
if absent). Admin routes require a signed cookie from `/admin/login`
(`ADMIN_PASSWORD` env var). Every screen below maps to exactly one endpoint.

### Public

| Method · Path | Body / Query | Returns | Screen |
|---|---|---|---|
| `POST /ask` | `{question, client_id?, session_id?, prompt_version?}` | `{request_id, route, answer, provenance{chunks[],sql{query,rows}}, guardrails[], status}` | 1, 2a/b/c |
| `GET /history` | `?client_id=` | `[{request_id, question, route, created_at, feedback, flagged}]` | 3 |
| `GET /requests/{id}` | — | public-safe detail: question, answer, route, provenance, guardrail reasons, own feedback | 2, 3 |
| `POST /requests/{id}/feedback` | `{thumbs, comment?}` | `{ok}` | 2 |
| `POST /replay` | `{request_id, prompt_version}` | new linked `request_id` + answer | 4 |
| `GET /provenance/source` | `?request_id=` | Wikipedia: `{text, highlights:[{start,end}]}`; FIA: `{pdf_path, page, highlight_text}`; SQL: `{query, rows}` | 2a/2c |

### Admin (all require admin cookie)

| Method · Path | Query | Returns | Screen |
|---|---|---|---|
| `POST /admin/login` | `{password}` | sets signed cookie | 5 |
| `GET /admin/overview` | `?range=` | KPI cards + requests/route/latency series + top flags + recent | 6 |
| `GET /admin/traces` | filters: route, status, client_id, prompt_version, range, flagged_only, page | paginated trace rows | 7 |
| `GET /admin/traces/{id}` | — | full trace: spans[], scores, flags, guardrails, feedback, raw JSON | 8 |
| `GET /admin/latency` | `?range=&route=` | p50/p95/p99, by-span-type breakdown, slowest[] | 9 |
| `GET /admin/cost` | `?range=` | today/week/month spend, by model/route/operation, token table, histogram | 10 |
| `GET /admin/quality` | `?range=` | RAGAS distributions, trend w/ prompt-version markers, faithfulness-vs-feedback scatter | 11 |
| `GET /admin/flags` | `?range=&flag=` | flag rules + counts + flagged-request table | 12 |
| `GET /admin/guardrails` | `?range=` | guardrail rules grouped by stage + counts + trends | 13 |
| `GET /admin/users` | — | per-client analytics rows | 14 |
| `GET /admin/users/{client_id}` | — | that client's full history | 14 |
| `GET /admin/feedback-loop` | — | the 3 before/after case studies | 15 |

---

## 5. Implementation plan (ordered, each step gated by sign-off)

| Step | What | Output | Depends on |
|---|---|---|---|
| **4.0** | **Confirm span-storage decision (§0)** | decision logged in `docs/decisions.md` | — |
| 4.1 | Postgres: docker-compose, schema/migrations for the 12 tables, connection layer | running DB + migration scripts | 4.0 |
| 4.2 | OpenTelemetry: SDK setup, span taxonomy (§3), wrap existing `rag/*` functions, custom processor → `spans` table | every `ask()` emits a full trace | 4.1 |
| 4.3 | Persistence: write `requests`/`route_decisions`/`sql_executions`/`request_chunks`/`chunks` on each ask | trace anchored end-to-end | 4.2 |
| 4.4 | Guardrails module: ~10 hand-rolled rules + Guardrails AI `DetectPII`; wire input/retrieval/output stages; write `guardrails_triggered` | guardrails enforced + logged | 4.3 |
| 4.5 | Scoring: RAGAS async job → `scores` | faithfulness/relevance per request | 4.3 |
| 4.6 | Flagging: rules over spans+scores → `flags` | bad answers flagged | 4.5 |
| 4.7 | FastAPI service: all public + admin endpoints (§4), client-id cookie, admin auth | API contract live | 4.3–4.6 |
| 4.8 | Replay + prompt-version registry | `/replay` works, linked runs | 4.7 |
| 4.9 | Frontend: Next.js, all 15 screens, TanStack Query, PDF.js + Wikipedia-highlight provenance components | the dashboard | 4.7 (Stitch designs feed this) |
| 4.10 | Seed/demo data: batch representative + known-failure questions (Verstappen-wins SQL hallucination, `sql_zero_results`, `route_misclassified`) | dashboards have real data | 4.7 |
| 4.11 | End-to-end verification | everything wired, screens populated | all |

**Phase 5** (separate): pick 3 real dashboard failures from 4.10, fix them,
capture before/after metrics → Screen 15.

---

## 6. New decisions this plan introduces (for `docs/decisions.md` once approved)

- **D4.1** Span storage = Postgres `spans` table. ✅ Accepted 2026-05-17 —
  logged in `docs/decisions.md`.
- **D4.2** One trace per `/ask`; async scoring/flagging in a linked trace so
  the user response isn't blocked on RAGAS.
- **D4.3** Replays are first-class `requests` rows linked via
  `replay_of_request_id` — never overwrite history (matches Screen 4).
- **D4.4** Prompt versions live in a small registry so replay + the
  quality-trend markers (Screen 11) have something to switch between.
