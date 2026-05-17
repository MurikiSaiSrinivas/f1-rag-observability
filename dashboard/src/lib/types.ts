/**
 * Typed contract — mirrors docs/phase-4-plan.md §2 (data model) and §4 (API).
 * The UI binds to THESE types. When the FastAPI backend lands, only
 * src/lib/api.ts changes; components and types stay put.
 */

export type Route = "narrative" | "structured" | "both";
export type FinalStatus = "success" | "error" | "refused" | "flagged";
export type GuardrailStage = "input" | "retrieval" | "output";
export type GuardrailAction =
  | "refuse"
  | "reject"
  | "sanitize"
  | "flag"
  | "block"
  | "warn";
export type Severity = "info" | "warning" | "critical";
export type SpanType =
  | "guardrail"
  | "llm"
  | "retrieval"
  | "sql"
  | "orchestration";
export type SourceKind = "wikipedia" | "fia";

/* ---------- Data model (12 tables) ---------- */

export interface Client {
  client_id: string;
  first_seen_at: string;
  last_seen_at: string;
  request_count: number;
}

export interface Session {
  session_id: string;
  client_id: string;
  started_at: string;
  last_activity_at: string;
}

export interface RequestRow {
  request_id: string;
  client_id: string;
  session_id: string;
  question: string;
  final_answer: string;
  route: Route;
  model: string;
  prompt_version: string;
  temperature: number;
  prompt_tokens: number;
  completion_tokens: number;
  embedding_tokens: number;
  total_cost_usd: number;
  latency_ms: number;
  final_status: FinalStatus;
  created_at: string;
  replay_of_request_id: string | null;
}

export interface RouteDecision {
  request_id: string;
  category: Route;
  confidence: number;
  reasoning: string;
  router_model: string;
  router_tokens: number;
  router_latency_ms: number;
}

export interface Chunk {
  chunk_id: string;
  source: SourceKind;
  source_file_path: string;
  char_start: number;
  char_end: number;
  page_number: number | null;
  title: string;
  url: string;
  text: string;
  metadata: Record<string, unknown>;
}

export interface RequestChunk {
  request_id: string;
  chunk_id: string;
  rank: number;
  similarity: number;
  used_in_prompt: boolean;
}

export interface SqlExecution {
  request_id: string;
  generated_sql: string;
  cleaned_sql: string;
  row_count: number;
  execution_ms: number;
  timed_out: boolean;
  error: string | null;
  result_rows: Record<string, unknown>[];
  gen_model: string;
  gen_tokens: number;
  gen_latency_ms: number;
}

export interface Span {
  span_id: string;
  request_id: string;
  parent_span_id: string | null;
  name: string;
  span_type: SpanType;
  start_ts: number;
  end_ts: number;
  duration_ms: number;
  status: "ok" | "error";
  attributes: Record<string, unknown>;
}

export interface Score {
  request_id: string;
  metric: "faithfulness" | "answer_relevancy" | "context_relevancy";
  value: number;
  scored_at: string;
  scorer_model: string;
}

export interface GuardrailTriggered {
  id: string;
  request_id: string;
  rule_name: string;
  stage: GuardrailStage;
  implementation: "hand_rolled" | "guardrails_ai";
  action: GuardrailAction;
  severity: Severity;
  reason: string;
  triggered_at: string;
}

export interface Flag {
  id: string;
  request_id: string;
  flag_name: string;
  description: string;
  severity: Severity;
  flagged_at: string;
}

export interface Feedback {
  id: string;
  request_id: string;
  thumbs: "up" | "down";
  comment: string | null;
  submitted_at: string;
}

/* ---------- API composites (§4) ---------- */

export interface AskResponse {
  request_id: string;
  route: Route;
  answer: string;
  status: FinalStatus;
  provenance: {
    chunks: (RequestChunk & Pick<Chunk, "title" | "source" | "text">)[];
    sql: { query: string; rows: Record<string, unknown>[] } | null;
  };
  guardrails: GuardrailTriggered[];
}

export interface HistoryItem {
  request_id: string;
  question: string;
  route: Route;
  created_at: string;
  feedback: "up" | "down" | null;
  flagged: boolean;
}

export interface TraceRow {
  request_id: string;
  created_at: string;
  client_id: string;
  question: string;
  route: Route;
  latency_ms: number;
  total_tokens: number;
  total_cost_usd: number;
  faithfulness: number | null;
  feedback: "up" | "down" | null;
  final_status: FinalStatus;
  flags: string[];
}

export interface TraceDetail {
  request: RequestRow;
  route_decision: RouteDecision;
  spans: Span[];
  request_chunks: (RequestChunk & Pick<Chunk, "title" | "source">)[];
  sql_execution: SqlExecution | null;
  scores: Score[];
  guardrails: GuardrailTriggered[];
  flags: Flag[];
  feedback: Feedback | null;
}

export interface AdminOverview {
  kpis: {
    total_requests: number;
    error_rate: number;
    avg_latency_ms: number;
    cost_today_usd: number;
    avg_faithfulness: number;
    feedback_ratio: number;
  };
  requests_over_time: { t: string; requests: number; errors: number }[];
  route_distribution: { route: Route; count: number }[];
  top_flags: { flag_name: string; count: number }[];
  recent: TraceRow[];
}

/* ---------- Public answer + provenance ---------- */

export interface ProvenanceSource {
  kind: SourceKind; // wikipedia | fia
  title: string;
  url: string;
  document_text: string; // full source text rendered in the reader
  highlights: { start: number; end: number; chunk_id: string }[];
  page_number: number | null; // FIA only
}

export interface AnswerRetrieved {
  chunk_id: string;
  rank: number;
  similarity: number;
  used_in_prompt: boolean;
  title: string;
  source: SourceKind;
}

export interface AnswerView {
  request_id: string;
  question: string;
  route: Route;
  answer: string;
  status: FinalStatus;
  retrieved: AnswerRetrieved[];
  source: ProvenanceSource | null; // narrative/both: highlighted reader
  sql: {
    query: string;
    rows: Record<string, unknown>[];
    row_count: number;
  } | null; // structured/both
  guardrails: GuardrailTriggered[];
  feedback: "up" | "down" | null;
}

export interface AskResult {
  request_id: string;
  route: Route;
}
