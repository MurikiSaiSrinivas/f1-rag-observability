# F1 RAG Observability — Dashboard Design Brief (for Google Stitch)

> Paste-ready prompts for generating the UI in Google Stitch. Faithful to the
> architecture locked 2026-05-14 (see `docs/project-reference.md` →
> "Observability architecture"). Section A sets the global visual language;
> paste it once / use as the project theme. Sections B feed Stitch **one screen
> at a time** — generate Screen 8 (admin Trace Detail) first; everything else
> echoes its visual language.

---

## A. GLOBAL DESIGN BRIEF (paste first / use as project theme)

```
PRODUCT
"F1 RAG Observability" — an AI question-answering app for Formula 1 (seasons
2020–2025) with a full observability layer behind it. Two distinct surfaces in
one product:
  1. PUBLIC APP — anyone (anonymous, no login) asks F1 questions and sees the
     answer PLUS full provenance: exactly which source text or database rows the
     answer came from.
  2. ADMIN COCKPIT — one password-protected admin who monitors every request
     across all users: traces, latency, cost, quality scores, guardrails, flags.

The observability layer is the real product; the F1 Q&A is the workload being
observed.

AUDIENCE
Public app: casual F1 fans. Friendly, fast, trustworthy.
Admin cockpit: an ML/platform engineer. Think Datadog / Grafana / Langfuse /
Honeycomb — dense, precise, scannable, no decoration that isn't data.

VISUAL LANGUAGE
- Admin cockpit: dark theme. Background near-black charcoal (#0E0F12), panels
  one step lighter (#16181D), 1px subtle borders (#262A31). Text near-white,
  secondary text muted grey.
- Public app: light theme, clean white/very-light-grey, same accent + type.
- Accent color: a single racing red (#E10600) used sparingly for primary
  actions, the active route, and key highlights. Status colors: green = healthy
  / success, amber = warning / flagged, red = error / failure.
- A subtle checkered-flag motif allowed ONLY as a faint texture in empty states
  and the login screen — never behind data.
- Typography: clean grotesque sans for UI (Inter-like). MONOSPACE for all IDs,
  SQL, JSON, latency numbers, token counts, similarity scores, request IDs.
- Layout: generous data density, 12-col grid, persistent left nav in the admin
  cockpit, top bar in the public app. Rounded-medium corners, soft shadows only
  on overlays/modals.
- Charts: minimal axis chrome, no gridline clutter, value-on-hover tooltips,
  consistent color legend across all screens.

SIGNATURE COMPONENT
A horizontal "trace waterfall": a request broken into time-ordered spans
(router → guardrails → embed → vector search → SQL gen → SQL exec → synthesis →
output guardrails), each span a horizontal bar whose length = its latency,
color-coded by span type, click to expand attributes (tokens, cost, model,
inputs/outputs). This is the hero view of the whole product.
```

---

## B. SCREENS

### PART 1 — PUBLIC APP (anonymous user, no login)

#### Screen 1 — Ask (home)

```
SCREEN: Public Q&A home, light theme.
A centered, generous search/ask experience. Large headline "Ask anything about
Formula 1 (2020–2025)". A big rounded question input with a red "Ask" button.
Three example-question chips below it that hint at the three answer types:
  - "Who is Lando Norris?"            (narrative)
  - "How many wins did Verstappen have in 2023?"  (structured / data)
  - "What happened at the 2021 Abu Dhabi GP and how did the title end?" (both)
Top bar: product name left, a "My history" link and a faint "Admin" link right.
Below the input, a subtle line: "No account needed — your questions are saved to
this browser only." Empty, calm, fast-feeling. Faint checkered texture in the
far background only.
```

#### Screen 2a — Narrative answer (Wikipedia source, highlighted text)

```
SCREEN: Answer view, light theme, two-column.
Left column (60%): the user's question at top; a small "Route" badge reading
"NARRATIVE" (grey pill); the AI's prose answer in readable body text; below the
answer a row of thumbs-up / thumbs-down buttons and an optional "Add a comment"
field; a "Replay this question" link.
Right column (40%), labeled "Where this answer came from": a source document
panel showing Wikipedia article text in a scrollable reader, with specific
passages HIGHLIGHTED in yellow — these are the exact chunks the answer used.
Above the document: the article title + a "Wikipedia" source tag. A small
control "Retrieved 5 · Used 3" with a toggle to show retrieved-but-unused chunks
dimmed vs. hidden.
If a guardrail fired, a non-blocking amber banner above the answer: "⚠ This
answer was flagged: low source similarity — treat with caution" with a
"Why?" expander showing the full guardrail reason.
```

#### Screen 2b — Structured answer (SQL provenance)

```
SCREEN: Answer view, light theme, two-column. Same layout as 2a but:
- Route badge reads "DATA / SQL" (blue pill).
- Right column "Where this answer came from" shows: (1) the generated SQL query
  in a monospace code block with syntax highlighting and a copy button, and
  (2) below it the result rows the query returned, as a clean data table with
  a "12 rows" count. A small caption: "This answer was computed directly from
  the F1 results database (Ergast), not retrieved text."
- Left column answer is the prose summary of those rows + thumbs + replay.
```

#### Screen 2c — Combined answer (both paths)

```
SCREEN: Answer view, light theme. Route badge reads "BOTH" (purple pill).
Right column is a tabbed provenance panel with two tabs:
  Tab 1 "Database" — the SQL query + returned rows table (as 2b).
  Tab 2 "Sources"  — the highlighted source document reader (as 2a), supporting
                     FIA-regulation PDFs too: a PDF.js-style page viewer showing
                     the actual PDF page, jumped to the relevant page number,
                     with the contributing sentence highlighted on the page.
A one-line note explains the answer combined exact data (authoritative) with
narrative context.
```

#### Screen 3 — My History

```
SCREEN: "My questions" list, light theme. A reverse-chronological list of this
browser's past questions only. Each row: the question text (truncated), a route
badge (NARRATIVE / DATA / BOTH), timestamp, a tiny feedback indicator (👍/👎/—),
and an amber dot if any guardrail fired. Clicking a row opens that question's
full Answer + Provenance view (Screen 2). Top: a search box to filter own
history. Empty state: friendly "You haven't asked anything yet" with the
checkered texture.
```

#### Screen 4 — Replay (prompt-version comparison)

```
SCREEN: Replay view, light theme, side-by-side comparison.
Header: the original question. A control to pick a different prompt version from
a dropdown ("v1 — baseline", "v2 — stricter grounding", etc.) and a red "Re-run"
button. Two columns side by side: LEFT "Original (v1)" and RIGHT "Replay (v2)".
Each column shows: the answer text, the route taken, latency, token count, and
the same provenance summary (chunks used / SQL). Differences between the two
answers are subtly highlighted. Footer note: replays don't overwrite history,
they're saved as linked runs.
```

---

### PART 2 — ADMIN OBSERVABILITY COCKPIT (password-gated, dark theme)

#### Screen 5 — Admin Login

```
SCREEN: Minimal admin login, dark theme (#0E0F12). Centered card: product name,
subtitle "Observability cockpit", a single password field, a red "Enter" button.
Faint checkered-flag texture behind the card. Small print: "Single admin,
password-protected. Public users don't see this." Error state: red inline
message "Incorrect password".
```

#### Screen 6 — Overview / System Health (admin landing)

```
SCREEN: Observability overview dashboard, dark cockpit theme, persistent left
nav. Left nav items: Overview, Traces, Trace Detail, Latency, Cost, Quality,
Flags / Bad Answers, Guardrails, Users. Top bar: a global time-range picker
(Today / 7d / 30d / custom) and a live/refresh indicator.

Top row: KPI stat cards (big number + sparkline + delta vs previous period):
  - Total requests
  - Error rate %
  - Avg end-to-end latency (ms)
  - Cost (today)  [admin-only metric]
  - Avg faithfulness score
  - Feedback ratio (👍 vs 👎)

Middle row, three panels:
  - "Requests over time" line chart, with errors overlaid in red.
  - "Route distribution" donut: narrative / structured / both shares.
  - "Latency p50 / p95 / p99" trend.

Bottom row:
  - "Top flags firing" horizontal bar list (flag rule → count).
  - "Recent requests" compact table (last 10): time, question (truncated),
    route badge, latency, cost, status dot, faithfulness. Row click → Trace
    Detail.
```

#### Screen 7 — Traces Explorer

```
SCREEN: Traces explorer, dark cockpit theme. The full searchable/filterable
table of EVERY request across ALL anonymous users. Sticky filter bar:
free-text search; filters for route (narrative/structured/both), status
(success/error/flagged), client_id, prompt version, time range; a "flagged only"
toggle. Dense data table, columns:
  request_id (mono, truncated) · time · client_id (mono) · question (truncated,
  hover full) · route badge · latency ms · tokens · cost $ · faithfulness ·
  feedback · status dot · flags (small chips).
Sortable headers, pagination, row click opens Trace Detail. Column to toggle
density. Selected-row highlight in accent red.
```

#### Screen 8 — Trace Detail (the hero screen)

```
SCREEN: Single-request trace detail, dark cockpit theme. THE signature screen.
Top header strip: question text, request_id, client_id, session_id, timestamp,
model, prompt_version, final status badge, total latency, total tokens, total
cost. A "Replay" and "Open public view" action.

MAIN: a horizontal SPAN WATERFALL timeline. Each span is a horizontal bar,
length proportional to its duration, vertically stacked in execution order,
color-coded by type:
  capture request · input guardrails · query router · embed question ·
  vector search (Chroma) · retrieval guardrails · generate SQL · execute SQL ·
  assemble context · LLM synthesis · output guardrails.
Hovering a span shows a tooltip; clicking expands a detail drawer for that span
with its attributes: inputs, outputs, latency, tokens in/out, cost, model,
errors. The router span shows the classification + confidence + reasoning. The
SQL spans show the generated query + row count + execution time. The vector
search span shows retrieved chunk IDs + similarity scores.

BELOW the waterfall, tabbed panels:
  - "Provenance": retrieved chunks list with rank, similarity, source, and a
    USED-IN-PROMPT flag (clearly distinguishing retrieved vs. actually used);
    plus SQL query + returned rows if structured; with links to view the
    highlighted source text / PDF page.
  - "Scores": RAGAS faithfulness, relevance, etc., as labeled gauges.
  - "Guardrails": every guardrail evaluated this request — name, stage
    (input/retrieval/output), passed/triggered, action taken, severity, full
    reason message.
  - "Flags": which flag rules fired (e.g. sql_execution_error, sql_zero_results,
    route_misclassified, hallucination) with explanation.
  - "Feedback": the user's 👍/👎 + comment if any.
  - "Raw": the full request/response JSON, monospace, collapsible.
```

#### Screen 9 — Latency Breakdown (admin-only)

```
SCREEN: Latency analysis, dark cockpit theme. Top: p50 / p95 / p99 end-to-end
latency big stats + trend line over the selected time range. Middle: a stacked
horizontal bar "average latency by span type" showing where time goes (router
vs embed vs vector search vs SQL exec vs synthesis), and a heatmap of latency
over time-of-day. Bottom: "Slowest requests" table (request, total latency,
dominant span, route) → click to Trace Detail. A route filter so latency can be
compared narrative vs structured vs both.
```

#### Screen 10 — Cost Meter (admin-only)

```
SCREEN: Cost dashboard, dark cockpit theme. Big stat cards: spend today / this
week / this month, with deltas. A cumulative spend area chart over time. A
breakdown: cost by model, cost by route (narrative/structured/both), cost by
operation (embedding vs SQL gen vs synthesis vs routing). A token-usage table
(prompt tokens, completion tokens, total) per day. A small callout banner noting
the project runs on the free OpenAI token program (lifetime spend ~$0.04) so
"cost" is tracked as if billed, for realism. A per-request cost distribution
histogram with an "excessive cost" threshold line marked.
```

#### Screen 11 — Quality Scores (admin-only)

```
SCREEN: Answer-quality dashboard, dark cockpit theme. RAGAS-style metric
distributions: faithfulness, answer relevance, context relevance — each as a
histogram with mean line. Trend lines of average faithfulness/relevance over
time, with prompt-version change markers overlaid (to see if a prompt change
regressed quality). A scatter of faithfulness vs. user feedback to spot
disagreement. A "lowest-faithfulness recent answers" table → Trace Detail.
```

#### Screen 12 — Flags / Bad Answers Dashboard (admin-only)

```
SCREEN: Bad-answers dashboard, dark cockpit theme. This is requirement #7 — the
debugging surface. Left: a list of flag rules (no-source-but-confident,
answer-contradicts-chunk, cost spike, prompt-version regression,
sql_execution_error, sql_zero_results, route_misclassified, hallucination) each
with a fire-count and trend sparkline; click to filter. Right/main: a table of
flagged requests with EVERYTHING needed to debug a failure in one row-expand:
question, chunks (retrieved + used), answer, prompt version, model, cost,
latency, faithfulness, user feedback, and the failure reason. Expanding a row
shows the mini trace + provenance inline; a deep-link to full Trace Detail.
Filter by flag type, route, time range.
```

#### Screen 13 — Guardrails Dashboard (admin-only)

```
SCREEN: Guardrails monitor, dark cockpit theme. A table/grid of all guardrail
rules grouped by stage: INPUT (off_topic, prompt_injection, pii_in_question,
empty_or_too_short, too_long), RETRIEVAL (low_similarity, empty_retrieval),
OUTPUT (hallucination, refused_but_should_answer, pii_in_answer,
excessive_cost). For each: implementation tag ("hand-rolled" or "Guardrails
AI"), trigger count, trend sparkline, action taken (refuse / sanitize / flag /
block), severity. Top: stacked bar of triggers by stage over time. Click a
guardrail → list of requests where it fired → Trace Detail. Note that one rule
(pii_in_question) is powered by the Guardrails AI library to contrast DIY vs
library approaches.
```

#### Screen 14 — Per-User Analytics (admin-only)

```
SCREEN: Anonymous-user analytics, dark cockpit theme. Since there are no
accounts, "users" are anonymous client_id browser identities. A table: client_id
(mono), first seen, last seen, # questions, route mix (tiny stacked bar), avg
faithfulness, feedback ratio, total cost attributed, # flagged. Click a
client_id → that user's full question history (admin can see all) with links to
each Trace Detail. A note on the accepted limitation: cleared cookies = new
identity.
```

#### Screen 15 — Feedback-Loop / Before-After (Phase 5 demo)

```
SCREEN: Feedback-loop case study view, dark cockpit theme. Built for the demo
narrative "trace → score → flag → debug → fix → retest". A picker of 3 chosen
real failures. For the selected one: a left "BEFORE" and right "AFTER" panel
showing the same question's answer, faithfulness score, flags, and latency/cost,
with the metric deltas highlighted (red → green). A middle "What we changed"
note (e.g. "tightened SQL schema prompt"). A small timeline showing the
fix commit and the metric moving after it. This sells the whole project: the
observability layer caught a real failure and the fix is measurable.
```

---

## Coverage check

- **8 observability requirements** — all mapped: capture (Screen 8 header), trace
  spans (Screen 8 waterfall), retrieval context (Screen 8 Provenance tab),
  system metrics (Screens 9, 10), quality scoring (Screen 11), flag bad answers
  (Screen 12), bad-answers dashboard (Screen 12), close the loop (Screen 15).
- **Provenance modes** — Wikipedia highlight (2a), FIA PDF.js (2c), SQL table
  (2b), all surfaced again in Screen 8.
- **Role split** — public: history, provenance, retrieved-vs-used, replay,
  thumbs, full guardrail reasons. Admin-only: cost, latency, bad-answers,
  flag-rules, guardrails dashboard, per-user analytics.
- **Identity** — anonymous `client_id`, single password admin (Screens 5, 14).
