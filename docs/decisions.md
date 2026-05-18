# Decision Log

Chronological record of design decisions for the F1 RAG Observability project, including options considered and rejected. Maintained as the project progresses — append new entries at the top of the relevant phase section.

**Status legend:** ✅ accepted · ❌ scratched · 🕒 deferred · 🔄 reversed

---

## Phase 4 — Observability layer (2026-05-17)

### D4.1 — Span storage backend
**Status:** ✅ Accepted
**Decision:** Emit genuine OpenTelemetry spans, but persist them in the Postgres `spans` table via a custom span processor. No separate trace backend. (Resolves deferred decision P4.A.)
**Considered but scratched:**
- ❌ Jaeger — its built-in trace UI competes with the custom Trace Detail screen, which is the actual deliverable; adds a separate service to run.
- ❌ Tempo + Grafana — heavier infra; meaningful at scale but overkill for a portfolio dataset of a few thousand requests.
- ❌ ClickHouse — columnar trace analytics; massive overkill at this scale, adds a columnar DB to operate for no benefit here.

**Reasoning:** The deliverable is a *bespoke* observability UI, not a generic trace explorer — a Jaeger/Tempo trace browser would only duplicate the dashboard we hand-build. Postgres-only keeps infra to one container and the latency screens become plain SQL. OpenTelemetry instrumentation is still real (interview-credible); swapping to an OTLP collector → Tempo later is a config change, noted in code. Consistent with the hand-rolled thesis (D3.2).

### D4.2 — One trace per /ask; async scoring
**Status:** ✅ Accepted (2026-05-17)
**Decision:** One OTel trace per `/ask`. RAGAS-style scoring + flagging run after the response via FastAPI `BackgroundTasks` so the user isn't blocked on the scorer.

### D4.3 — Replays are first-class linked rows
**Status:** ✅ Accepted (2026-05-17)
**Decision:** A replay is a normal `requests` row with `replay_of_request_id` set — history is never overwritten. `GET /replay/{id}` runs the question under prompt-version v2 and returns the original-vs-replay comparison.

### D4.4 — Prompt-version registry
**Status:** ✅ Accepted (2026-05-17)
**Decision:** `prompt_versions` table seeded with v1 (baseline) / v2 (stricter grounding). Threaded through `requests.prompt_version` for replay + the Quality screen's prompt-change markers.

### D4.5 — Guardrails: hand-rolled, Guardrails AI deferred
**Status:** ✅ Accepted with a deferred sub-item
**Decision:** All ~11 guardrail rules implemented hand-rolled (regex/heuristics), including `pii_in_question`. The locked architecture wanted ONE rule via the Guardrails AI library to show DIY-vs-library fluency.
**Considered but scratched (for now):**
- 🕒 Guardrails AI `DetectPII` — pulls Presidio + spaCy models; heavy and version-fragile to install on this Python/OS, a real risk to a mid-build backend. Deferred; the swap is one function (`obs/guardrails._pii_match`) behind an unchanged seam. Revisit when hardening deps.

### D4.6 — Scoring: gpt-4o-mini LLM-judge, not the ragas package
**Status:** ✅ Accepted with a deferred sub-item
**Decision:** Faithfulness / answer_relevancy / context_relevancy computed by a single strict-JSON gpt-4o-mini judge call (`obs/scoring.py`), not the `ragas` package.
**Reasoning:** `ragas` drags in datasets/langchain and issues its own LLM calls — heavy, version-fragile, and slow. The metrics + the `scores` table contract are identical; swapping in real RAGAS later is localized behind `score_request`. 🕒 Revisit when hardening.

### D4.7 — Admin auth not yet enforced
**Status:** 🕒 Deferred (hardening follow-up)
**Decision:** `/admin/login` sets a cookie but admin endpoints are not hard-gated yet — the Next app has no login wiring in the live-API swap and gating now would break the demo. Enforce the signed-cookie check as a hardening pass before any public deployment (ties into P5.A).

---

## Phase 3 — Routed RAG + SQL pipeline (2026-05-14)

### D3.4 — Query router implementation
**Status:** ✅ Accepted
**Decision:** LLM-based classifier with structured-output JSON: `{category: "structured" | "narrative" | "both", confidence: 0.0-1.0, reasoning: str}`. Runs once per request before retrieval, using `gpt-4o-mini`.
**Considered but scratched:**
- ❌ Rule-based (keyword/regex matching) — brittle to phrasing, no observability signal, hard to maintain as categories grow.
- ❌ Hybrid (rules first, LLM fallback) — adds complexity without clear win.

**Reasoning:** The router decision itself becomes a richly traceable Phase 4 span (confidence + reasoning fields). Misclassifications surface as a flag rule (`route_misclassified`). More observable, which is the project's whole point.

### D3.3 — Ergast SQL schema shape
**Status:** ✅ Accepted
**Decision:** 9 normalized tables: `drivers`, `constructors`, `circuits`, `races`, `race_results`, `qualifying_results`, `sprint_results`, `driver_standings`, `constructor_standings`. Natural composite keys (e.g., `(season, round)` for races, `(season, round, driver_id)` for results). Both `position` (INTEGER, NULL on DNF) and `position_text` (TEXT, Ergast literal) preserved. `status` as free text for queries like `WHERE status = 'Engine'`. Foreign keys enabled. Read-only mode at query time (`mode=ro`) to harden against LLM-hallucinated DDL/DML.
**Considered but scratched:**
- ❌ JSON-column dump (one table with JSON content column) — easier to load, but reads worse in interviews and forces SQL generator to know JSON path syntax.
- ❌ Surrogate INTEGER primary keys — natural keys debug better in queries, no extra JOINs to look up.
- ❌ Status lookup table — overkill for 6 seasons; free-text gives richer LLM-generated queries.

**Reasoning:** Standard normalization gives the SQL generator a clean schema to reason over. Demonstrates DB design skill for interviews.

### D3.2 — RAG framework
**Status:** ✅ Accepted
**Decision:** Hand-rolled — direct `openai.chat.completions.create` calls, direct Chroma `collection.query` calls, our own f-string prompt templates, our own pipeline orchestration. No LangChain or LlamaIndex.
**Considered but scratched:**
- ❌ LangChain — abstraction layers (callbacks, chains, runnables) fight clean OpenTelemetry span hierarchy; version churn breaks code; dep bloat.
- ❌ LlamaIndex — same downsides as LangChain.

**Reasoning:** Project's thesis is observability over RAG. Hand-rolled gives clean trace control over every step. Stronger interview signal ("here's exactly what my pipeline does, step by step") than wiring a framework. Code comments will reference equivalent LangChain patterns to show fluency without paying the dependency cost.

### D3.1 — LLM provider + model
**Status:** ✅ Accepted
**Decision:** OpenAI `gpt-4o-mini` for synthesis + routing + SQL generation. Effectively $0 cost under the OpenAI data-sharing-for-tokens program (2.5M tokens/day, mini tier — comfortably covers our entire Phase 3-5 needs).
**Considered but scratched:**
- ❌ OpenAI `gpt-4o` — also free (250K/day) but tends to over-correct; produces fewer "interesting" failures for the dashboard to surface.
- ❌ `gpt-5` family — newer, less battle-tested; fewer interview reference points.
- ❌ Anthropic `claude-haiku-4-5` — no free tier; Claude Max plan doesn't cover API; we'd pay $1/$5 per 1M tokens.

**Reasoning:** Production-realistic, fast, well-documented. Mini = sweet spot for failure-mode variety. API is identical to gpt-4o, so easy to swap per-request for one-off comparisons later.

---

## Phase 2 — Chunking, embedding, indexing (2026-05-14)

### D2.11 — Wikipedia chunker design
**Status:** ✅ Accepted
**Decision:** Char-based sliding window, ~2,000 char target with ~200 char overlap. Snap chunk boundaries to paragraph break (`\n\n`) > sentence break (`. `) > hard cut. Min chunk 200 chars. Tiktoken verification after chunking (warn if outside 400-600 tokens).
**Considered but scratched:**
- ❌ Token-based windowing — tiktoken doesn't cleanly expose token→char mapping; char-based gets offsets for free.

**Reasoning:** Char offsets into the original `.txt` are needed for Phase 4 highlight UI; deriving them from token boundaries is more fragile.

### D2.10 — Wikipedia boilerplate stripping
**Status:** ✅ Accepted
**Decision:** Strip from earliest end-of-article header onward. Match exactly: `See also` / `References` / `External links` / `Further reading` / `Bibliography` / `Citations` / `Sources`. Char offsets reference the **original** `.txt` (not the stripped version).
**Considered but scratched:**
- ❌ Include `Notes` in the boilerplate keyword list — too ambiguous; appears mid-article as a footnote section header (e.g., for race-result footnotes).

### D2.9 — Two-path routed pipeline 🔄
**Status:** ✅ Accepted (revised mid-Phase 2)
**Decision:** Vector RAG for Wikipedia + FIA chunks; SQL on a normalized Ergast SQLite store for structured-fact questions. Query router (LLM call early in pipeline) classifies each question as `structured` / `narrative` / `both` and dispatches.
**Reversed from D2.8 below.** Original plan was to embed all three sources (including Ergast as synthesized sentences).
**Considered but scratched:**
- ❌ Unified RAG across all sources — fails on counting/aggregation questions because top-K retrieval can't surface all matching rows.
- ❌ Pre-compute summary chunks per (driver, season) to mitigate RAG counting weakness — would solve the demo failure case prematurely; dilutes Phase 4 observability story.

**Reasoning:** Production-grade pattern. RAG over JSON tables can't reliably count. Routing gives the dashboard richer observability (route-decision spans, SQL-execution spans, multiple failure-mode classes).

### D2.8 — Ergast chunker (one chunk per JSON record) 🔄
**Status:** ❌ Scratched (briefly accepted, then reversed by D2.9)
**Decision (original):** One chunk per Ergast JSON record converted to a natural-language sentence with deterministic chunk_id and metadata. Estimated ~6,575 chunks.
**Reason scratched:** Routed-pipeline pivot moved Ergast to a SQL path. Structured data + SQL >> structured data + RAG for counting/aggregation questions.

### D2.7 — FIA chunker design
**Status:** ✅ Accepted
**Decision:** Paragraph-aware chunking ~750 tokens. Track `page_number` for PDF.js navigation. De-hyphenate cross-line word breaks (`tech-\nnical` → `technical`). `source_file_path` points at the PDF (not the extracted `.txt`).
**Reasoning:** Regulatory text is dense + hierarchically numbered + full of cross-references — larger chunks preserve context. PDF path needed because dashboard renders the actual PDF, not the extracted text.

### D2.6 — Data cleaning policy
**Status:** ✅ Accepted

| Will do | Won't do |
|---|---|
| Strip Wikipedia end-of-article boilerplate | Lowercase / stem / lemmatize |
| Collapse runs of whitespace and blank lines | Remove typos, weird Unicode (e.g., `P�rez`) |
| De-hyphenate PDF cross-line word breaks | Fix factual errors |
| Drop chunks shorter than 50 chars | Resolve Wikipedia ambiguity |
| Deduplicate identical chunks | Filter by quality |

**Reasoning:** Clean only what's mechanically broken. Content-level noise is exactly what observability is designed to surface — sanitizing it kills the demo cases.

### D2.5 — Chunk metadata schema
**Status:** ✅ Accepted
**Decision:** Each chunk carries `chunk_id` (deterministic, stable across re-runs), `source`, `source_file_path`, `char_start`/`char_end` (Wikipedia + FIA), `page_number` (FIA), `text`, `title`, `url`, `metadata` (source-specific).
**Reasoning:** Captures enough metadata at Phase 2 to power Phase 4 provenance UI without a re-chunk/re-embed cycle later.

### D2.4 — Embedding cost containment
**Status:** ✅ Accepted
**Decision:** $20/mo hard cap on OpenAI dashboard (user-set before any API call); embed script defaults to `--dry-run` (counts tokens via tiktoken, prints estimated cost, no API call); `--confirm` required for actual API calls; resumable (existing chunk_ids in output are skipped).
**Reasoning:** No surprise charges. Explicit human gate before spending.

### D2.3 — Vector store
**Status:** ✅ Accepted
**Decision:** Chroma, local SQLite-backed persistence at `data/index/chroma/`. Gitignored.
**Reasoning:** Embedded, no server, matches "prefer standard primitives" principle. Adequate for ~5K chunks.

### D2.2 — Phase 2 dependencies
**Status:** ✅ Accepted
**Decision:** Add `openai`, `tiktoken`, `chromadb`, `python-dotenv` via `uv add` (auto-resolves versions, updates `uv.lock`).
**Side observation:** Chromadb's transitive deps pull in OpenTelemetry, Pydantic, Uvicorn — Phase 4 stack arrives early "for free."

### D2.1 — Embedding model
**Status:** ✅ Accepted (locked 2026-05-14)
**Decision:** OpenAI `text-embedding-3-small` ($0.02 / 1M tokens, hosted).
**Considered but scratched:**
- ❌ Local `sentence-transformers` — would save trivial money (corpus is ~2M tokens, ~$0.04 total), adds 80-500MB model dependency, more friction.

**Reasoning:** Cost is a rounding error. One API key covers embedding + Phase 3 LLM.

---

## Observability architecture (locked 2026-05-14, before Phase 2 code)

### D-Obs.7 — Phase 4 data model (Postgres tables)
**Status:** ✅ Accepted
**Tables:** `clients`, `sessions`, `requests`, `request_chunks`, `chunks`, `spans`, `scores`, `flags`, `sql_executions`, `route_decisions`, `guardrails_triggered`, `feedback`.

### D-Obs.6 — Feature scope by role

| Feature | Users | Admin | Status |
|---|---|---|---|
| Own question + answer history | ✅ | ✅ all users | accepted |
| Retrieved vs. used-in-prompt distinction | ✅ | ✅ | accepted |
| Replay past question with different prompt | ✅ | ✅ | accepted |
| Thumbs up/down + comment | ✅ | ✅ | accepted |
| Full guardrail trigger reasons | ✅ | ✅ | accepted |
| Cost meter ($-spent today/week/month) | ❌ | ✅ | accepted |
| Latency breakdown per span | ❌ | ✅ | accepted |
| Bad Answers dashboard | ❌ | ✅ | accepted |
| Flag-rules dashboard | ❌ | ✅ | accepted |
| Per-user analytics | ❌ | ✅ | accepted |

**Considered but scratched:**
- ❌ Streaming LLM responses (token-by-token) — complicates trace capture; defer to post-Phase 5.
- ❌ Real-time WebSocket dashboard updates — polling every 3s is 10× simpler and indistinguishable for users.
- ❌ Multi-tenant data isolation (Postgres row-level security) — overkill for single-org portfolio scope.

### D-Obs.5 — Guardrail reason visibility
**Status:** ✅ Accepted (option C)
**Decision:** Full guardrail trigger reason shown to **all users** (not just admin).
**Considered but scratched:**
- ❌ Option A — admin-only visibility.
- ❌ Option B — soft warning ("This answer may not be fully supported") to users + full reason to admin.

**Reasoning:** Maximum transparency. Makes the dashboard educational, not just diagnostic.

### D-Obs.4 — Guardrails
**Status:** ✅ Accepted
**Decision:** Hand-rolled rules for ~10 cases (off-topic, prompt-injection, length checks, retrieval guards, hallucination via RAGAS, PII-in-answer regex, cost spike, etc.) + Guardrails AI library for `DetectPII` on input.
**Considered but scratched:**
- ❌ All-library approach (Guardrails AI / NeMo Guardrails for everything) — less granular control over what gets traced; harder to instrument cleanly.
- ❌ All-hand-rolled — misses the portfolio signal of library familiarity.

**Reasoning:** Mix demonstrates fluency with both DIY rules and standard guardrail libraries — interview asset.

### D-Obs.3 — Provenance UI per source
**Status:** ✅ Accepted
- **Wikipedia:** open `.txt` in a content panel, highlight `char_start:char_end` in yellow.
- **FIA:** PDF.js viewer; navigate to `page_number`; sentence highlighting via PDF.js text-layer search (no coordinate math required).
- **Ergast (SQL answers):** show generated SQL query + result rows in a table view.

**Considered but scratched:**
- ❌ Pixel-perfect bounding-box highlighting in PDFs — doubles chunker complexity; text-layer is good enough for single-column regulation PDFs.
- ❌ Page-level navigation only (no sentence highlight in PDFs) — user wanted explicit sentence-level visual confirmation.

### D-Obs.2 — Admin auth
**Status:** ✅ Accepted
**Decision:** Single admin role; password in `ADMIN_PASSWORD` env var; signed cookie after login.
**Reasoning:** Simple, no third-party auth service, sufficient for portfolio scope.

### D-Obs.1 — Identity (no user accounts)
**Status:** ✅ Accepted
**Decision:** Anonymous browser UUID stored in cookie/localStorage as `client_id`. Each user sees only their own history; admin sees all.
**Considered but scratched:**
- ❌ Real user accounts (OAuth / Clerk / Auth0) — a week of plumbing that doesn't strengthen the observability story.

**Accepted limitations:** cleared cookies → new identity; different devices → different identities.

---

## Phase 1 — Data collection (2026-05-11)

### D1.10 — Drivers without Wikipedia URLs (defensive)
**Status:** ✅ Accepted
**Decision:** Skip Ergast driver/constructor records that lack a `url` field; log at DEBUG.
**Context:** 14 FP1/reserve drivers in 2025 data (Paul Aron, Pato O'Ward, Dino Beganovic, etc.) have no Wikipedia URLs yet. Real data-quality finding — exactly the kind of messiness the project is meant to surface.

### D1.9 — FIA: latest issue only
**Status:** ✅ Accepted
**Decision:** Per year, download only the latest sporting + latest technical regulation issue. (Some years publish ≥5 issues with amendments throughout the season.)
**Reasoning:** Avoids redundant chunking of amendment text. Aligns with "minimal RAG" principle.

### D1.8 — FIA PDF acquisition
**Status:** ✅ Accepted
**Decision:** Manual download by the user — place PDFs at `data/raw/fia/{year}/{sporting|technical}.pdf`. Collector extracts text per page via pypdf.
**Considered but scratched:**
- ❌ Web scraping FIA regulation pages — fragile (URL structure changes yearly); against-spirit of TOS.

### D1.7 — Wikipedia URL harvest source
**Status:** ✅ Accepted
**Decision:** Harvest Wikipedia URLs by walking previously-collected Ergast files (`races.json` embeds race + circuit URLs; `drivers.json` + `constructors.json` embed driver/constructor URLs). Dedupe by URL.
**Considered but scratched:**
- ❌ Hardcoded Wikipedia URL list — fragile; would require manual updates per season.

**Reasoning:** Ergast already has the URLs; using them keeps article selection tied to the data we actually have.

### D1.6 — Politeness (rate limiting, retries, identity)
**Status:** ✅ Accepted
**Decision:** Custom `USER_AGENT` for Ergast and Wikipedia HTTP clients. Throttle: 0.3s for Ergast, 1.0s for Wikipedia. Tenacity retries: 3 attempts, exponential backoff.
**Reasoning:** Respect rate limits; identify the client.

### D1.5 — Per-run logs
**Status:** ✅ Accepted
**Decision:** Timestamped log file per `collect()` call at `logs/collect_{source}_{ts}.log`. DEBUG to file, WARNING+ to stderr (so tqdm progress bars stay readable).

### D1.4 — Resumability
**Status:** ✅ Accepted
**Decision:** All Phase 1 collectors skip files that already exist on disk. Safe to re-run.

### D1.3 — Per-source collector modules
**Status:** ✅ Accepted
**Decision:** Separate modules under `ingestion/collect/{ergast,wikipedia,fia}.py` with shared logger helper in `ingestion/_log.py`. Single CLI dispatcher at `scripts/collect.py --source ...`.

### D1.2 — Raw storage layout
**Status:** ✅ Accepted
**Decision:** Raw files on filesystem under `data/raw/{source}/...`; one JSONL manifest at `data/manifest.jsonl` (one row per source document).
**Considered but scratched:**
- ❌ Database for raw corpus — premature; filesystem + manifest gives audit + resumability without a DB dependency at this phase.

### D1.1 — Three data sources
**Status:** ✅ Accepted
**Decision:**
- **Ergast / Jolpica REST API** — race results, qualifying, standings, drivers, constructors, circuits, sprints.
- **Wikipedia** — race summaries, driver bios, constructor pages, circuit pages.
- **FIA regulation PDFs** — sporting + technical regs, 2020-2025.

**Reasoning:** Mix of structured + narrative + regulatory creates the messy, multi-source corpus the project needs to make observability interesting.

---

## Phase 0 — Scope lock (2026-05-10)

### D0.6 — Tentative tech stack
**Status:** ✅ Accepted (frameworks) / 🕒 Deferred (specific implementations)
**Decision:**
- Backend: Python + FastAPI + Pydantic + Uvicorn.
- Vector store: Chroma.
- App DB: Postgres (Phase 4).
- Tracing: OpenTelemetry.
- Scoring: RAGAS.
- Dashboard: Next.js + Tailwind + shadcn + TanStack Query.
- Python env: uv.

### D0.5 — Eight observability requirements
**Status:** ✅ Accepted
1. Capture the request (question, session ID, timestamp, model, prompt version, temperature, environment).
2. Trace pipeline as spans (router → retriever → chunks → LLM → tools → response).
3. Store retrieval context (chunk IDs, similarity scores, source names).
4. Track system metrics (latency, tokens, cost, error rate, retries).
5. Score answer quality (faithfulness, relevance, hallucination, safety, cost, user feedback).
6. Flag bad answers (no-source-but-confident, answer-contradicts-chunk, cost spike, prompt-version regression).
7. Bad Answers dashboard (per flagged trace).
8. Close the feedback loop (trace → score → flag → debug → fix → retest).

### D0.4 — Minimal RAG principle
**Status:** ✅ Accepted
**Decision:** RAG stays intentionally simple. No reranking, hybrid search, query rewriting, or fancy retrieval until a real dashboard failure justifies it.
**Reasoning:** Improvements are data-driven, not speculative. Premature complexity would create RAG quality but starve the observability layer of failures.

### D0.3 — Scope boundaries
**Status:** ✅ Accepted
**Decision:**
- Seasons 2020-2025 only.
- English text only.
- No images, no telemetry, no real-time data.

### D0.2 — Six-phase plan
**Status:** ✅ Accepted
**Decision:** Phase 0 scope lock → Phase 1 data collection → Phase 2 chunking/embedding/indexing → Phase 3 basic RAG + SQL pipeline → Phase 4 observability layer (the actual product, largest phase) → Phase 5 feedback loop demo (pick 3 real failures, fix, document before/after).

### D0.1 — Mission
**Status:** ✅ Accepted
**Decision:** **Observability is the product, RAG is the workload being observed.** F1 chosen as substrate for messy multi-source data, natural ambiguity (similar driver names, season-specific stats, team name changes), and inherent counting/temporal complexity.
**Reasoning:** Portfolio/interview value is in the observability layer, not in building yet another RAG. Building RAG that's intentionally minimal-and-flawed gives the observability layer real failures to surface.

---

## Currently deferred (revisit at the right phase)

| ID | Decision | Phase | Tentative pick |
|---|---|---|---|
| 🕒 P5.A | Deployment target | 5 | Local-only vs free-tier split (Vercel + Render + Neon, recommended) vs single VPS |

**Resolved 2026-05-17:** P4.A → D4.1 (span storage = Postgres `spans` table; OTel still emitted, custom processor persists to Postgres).
**Resolved 2026-05-14:** D3.1 (LLM = gpt-4o-mini), D3.2 (RAG framework = hand-rolled), D3.3 (SQL schema = 9 relational tables), D3.4 (query router = LLM classifier).

---

## How to use this log

- **Append, don't rewrite.** When a decision changes, mark the old entry 🔄 and add a new one explaining why.
- **One decision per entry.** If a topic has multiple related decisions, give each its own ID.
- **ID format:** `D{phase}.{N}` where N counts up within the phase. Decisions affecting observability arch carry the `D-Obs.N` prefix.
- **Order:** newest at top within each phase section.
- **Cross-reference** when one decision reverses or supersedes another (e.g., D2.9 reversed D2.8).
