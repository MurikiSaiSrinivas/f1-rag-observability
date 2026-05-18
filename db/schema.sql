-- F1 RAG Observability — app database schema (Phase 4, D4.1).
-- 12 trace tables + a small prompt-version registry (D4.4).
-- Hand-rolled DDL applied by scripts/migrate.py (no Alembic — matches D3.2).
-- IDs are app-style strings (req_*, cl_*, ses_*, sp_*), stored as TEXT.

CREATE TABLE IF NOT EXISTS clients (
  client_id      TEXT PRIMARY KEY,
  first_seen_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  request_count  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
  session_id        TEXT PRIMARY KEY,
  client_id         TEXT NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
  started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_activity_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS prompt_versions (
  version        TEXT PRIMARY KEY,
  label          TEXT NOT NULL,
  system_prompt  TEXT NOT NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS requests (
  request_id            TEXT PRIMARY KEY,
  client_id             TEXT NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
  session_id            TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  question              TEXT NOT NULL,
  final_answer          TEXT NOT NULL DEFAULT '',
  route                 TEXT NOT NULL,
  model                 TEXT NOT NULL,
  prompt_version        TEXT NOT NULL,
  temperature           DOUBLE PRECISION NOT NULL DEFAULT 0.2,
  prompt_tokens         INTEGER NOT NULL DEFAULT 0,
  completion_tokens     INTEGER NOT NULL DEFAULT 0,
  embedding_tokens      INTEGER NOT NULL DEFAULT 0,
  total_cost_usd        DOUBLE PRECISION NOT NULL DEFAULT 0,
  latency_ms            INTEGER NOT NULL DEFAULT 0,
  final_status          TEXT NOT NULL DEFAULT 'success',
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  replay_of_request_id  TEXT REFERENCES requests(request_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS route_decisions (
  request_id         TEXT PRIMARY KEY REFERENCES requests(request_id) ON DELETE CASCADE,
  category           TEXT NOT NULL,
  confidence         DOUBLE PRECISION NOT NULL DEFAULT 0,
  reasoning          TEXT NOT NULL DEFAULT '',
  router_model       TEXT NOT NULL DEFAULT '',
  router_tokens      INTEGER NOT NULL DEFAULT 0,
  router_latency_ms  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS chunks (
  chunk_id          TEXT PRIMARY KEY,
  source            TEXT NOT NULL,
  source_file_path  TEXT NOT NULL DEFAULT '',
  char_start        INTEGER,
  char_end          INTEGER,
  page_number       INTEGER,
  title             TEXT NOT NULL DEFAULT '',
  url               TEXT NOT NULL DEFAULT '',
  text              TEXT NOT NULL DEFAULT '',
  metadata          JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS request_chunks (
  request_id      TEXT NOT NULL REFERENCES requests(request_id) ON DELETE CASCADE,
  chunk_id        TEXT NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
  rank            INTEGER NOT NULL,
  similarity      DOUBLE PRECISION NOT NULL,
  used_in_prompt  BOOLEAN NOT NULL DEFAULT false,
  PRIMARY KEY (request_id, chunk_id)
);

CREATE TABLE IF NOT EXISTS sql_executions (
  request_id      TEXT PRIMARY KEY REFERENCES requests(request_id) ON DELETE CASCADE,
  generated_sql   TEXT NOT NULL DEFAULT '',
  cleaned_sql     TEXT NOT NULL DEFAULT '',
  row_count       INTEGER NOT NULL DEFAULT 0,
  execution_ms    INTEGER NOT NULL DEFAULT 0,
  timed_out       BOOLEAN NOT NULL DEFAULT false,
  error           TEXT,
  result_rows     JSONB NOT NULL DEFAULT '[]'::jsonb,
  gen_model       TEXT NOT NULL DEFAULT '',
  gen_tokens      INTEGER NOT NULL DEFAULT 0,
  gen_latency_ms  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS spans (
  span_id         TEXT PRIMARY KEY,
  request_id      TEXT NOT NULL REFERENCES requests(request_id) ON DELETE CASCADE,
  parent_span_id  TEXT,
  name            TEXT NOT NULL,
  span_type       TEXT NOT NULL,
  start_ts        DOUBLE PRECISION NOT NULL DEFAULT 0,
  end_ts          DOUBLE PRECISION NOT NULL DEFAULT 0,
  duration_ms     DOUBLE PRECISION NOT NULL DEFAULT 0,
  status          TEXT NOT NULL DEFAULT 'ok',
  attributes      JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scores (
  request_id    TEXT NOT NULL REFERENCES requests(request_id) ON DELETE CASCADE,
  metric        TEXT NOT NULL,
  value         DOUBLE PRECISION NOT NULL,
  scored_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  scorer_model  TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (request_id, metric)
);

CREATE TABLE IF NOT EXISTS guardrails_triggered (
  id              BIGSERIAL PRIMARY KEY,
  request_id      TEXT NOT NULL REFERENCES requests(request_id) ON DELETE CASCADE,
  rule_name       TEXT NOT NULL,
  stage           TEXT NOT NULL,
  implementation  TEXT NOT NULL,
  action          TEXT NOT NULL,
  severity        TEXT NOT NULL,
  reason          TEXT NOT NULL DEFAULT '',
  triggered_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS flags (
  id           BIGSERIAL PRIMARY KEY,
  request_id   TEXT NOT NULL REFERENCES requests(request_id) ON DELETE CASCADE,
  flag_name    TEXT NOT NULL,
  description  TEXT NOT NULL DEFAULT '',
  severity     TEXT NOT NULL DEFAULT 'warning',
  flagged_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS feedback (
  id            BIGSERIAL PRIMARY KEY,
  request_id    TEXT NOT NULL REFERENCES requests(request_id) ON DELETE CASCADE,
  thumbs        TEXT NOT NULL,
  comment       TEXT,
  submitted_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_requests_created   ON requests (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_requests_client    ON requests (client_id);
CREATE INDEX IF NOT EXISTS idx_requests_route     ON requests (route);
CREATE INDEX IF NOT EXISTS idx_requests_status    ON requests (final_status);
CREATE INDEX IF NOT EXISTS idx_spans_request      ON spans (request_id);
CREATE INDEX IF NOT EXISTS idx_reqchunks_request  ON request_chunks (request_id);
CREATE INDEX IF NOT EXISTS idx_guardrails_request ON guardrails_triggered (request_id);
CREATE INDEX IF NOT EXISTS idx_flags_request      ON flags (request_id);
CREATE INDEX IF NOT EXISTS idx_scores_request     ON scores (request_id);
