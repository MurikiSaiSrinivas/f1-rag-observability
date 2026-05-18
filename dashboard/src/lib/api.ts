/**
 * The single swap point between mock data and the real FastAPI backend.
 *
 * Today: USE_MOCK is true -> typed fixtures from src/lib/mock.ts.
 * Phase 4: set NEXT_PUBLIC_API_BASE and flip USE_MOCK -> these same function
 * signatures fetch the real endpoints. No component or type changes.
 */
import {
  askMock,
  MOCK_COST,
  MOCK_FEEDBACK_LOOP,
  MOCK_FLAGS,
  MOCK_GUARDRAILS,
  MOCK_HISTORY,
  MOCK_LATENCY,
  MOCK_OVERVIEW,
  MOCK_QUALITY,
  MOCK_TRACES,
  MOCK_USERS,
  mockAnswerView,
  mockReplay,
  mockTraceDetail,
  mockUserDetail,
} from "@/lib/mock";
import type {
  AdminOverview,
  AnswerView,
  AskResult,
  CostView,
  FeedbackLoopCase,
  FlagsView,
  GuardrailsView,
  HistoryItem,
  LatencyView,
  QualityView,
  ReplayComparison,
  TraceDetail,
  TraceRow,
  UserDetail,
  UserRow,
} from "@/lib/types";

const USE_MOCK = process.env.NEXT_PUBLIC_API_BASE ? false : true;
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { credentials: "include" });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json() as Promise<T>;
}

// Simulate network so loading states are real during the mock phase.
const delay = <T>(value: T, ms = 350): Promise<T> =>
  new Promise((r) => setTimeout(() => r(value), ms));

export const api = {
  getOverview(): Promise<AdminOverview> {
    return USE_MOCK
      ? delay(MOCK_OVERVIEW)
      : get<AdminOverview>("/admin/overview");
  },
  getTraces(): Promise<TraceRow[]> {
    return USE_MOCK ? delay(MOCK_TRACES) : get<TraceRow[]>("/admin/traces");
  },
  getTraceDetail(id: string): Promise<TraceDetail> {
    return USE_MOCK
      ? delay(mockTraceDetail(id))
      : get<TraceDetail>(`/admin/traces/${id}`);
  },
  getHistory(): Promise<HistoryItem[]> {
    return USE_MOCK ? delay(MOCK_HISTORY) : get<HistoryItem[]>("/history");
  },
  ask(question: string): Promise<AskResult> {
    if (USE_MOCK) return delay(askMock(question), 600);
    return fetch(`${API_BASE}/ask`, {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ question }),
    }).then((r) => r.json() as Promise<AskResult>);
  },
  getAnswer(id: string): Promise<AnswerView> {
    return USE_MOCK
      ? delay(mockAnswerView(id))
      : get<AnswerView>(`/requests/${id}`);
  },
  getLatency(): Promise<LatencyView> {
    return USE_MOCK ? delay(MOCK_LATENCY) : get<LatencyView>("/admin/latency");
  },
  getCost(): Promise<CostView> {
    return USE_MOCK ? delay(MOCK_COST) : get<CostView>("/admin/cost");
  },
  getQuality(): Promise<QualityView> {
    return USE_MOCK ? delay(MOCK_QUALITY) : get<QualityView>("/admin/quality");
  },
  getFlags(): Promise<FlagsView> {
    return USE_MOCK ? delay(MOCK_FLAGS) : get<FlagsView>("/admin/flags");
  },
  getGuardrails(): Promise<GuardrailsView> {
    return USE_MOCK
      ? delay(MOCK_GUARDRAILS)
      : get<GuardrailsView>("/admin/guardrails");
  },
  getUsers(): Promise<UserRow[]> {
    return USE_MOCK ? delay(MOCK_USERS) : get<UserRow[]>("/admin/users");
  },
  getUser(id: string): Promise<UserDetail> {
    return USE_MOCK
      ? delay(mockUserDetail(id))
      : get<UserDetail>(`/admin/users/${id}`);
  },
  getFeedbackLoop(): Promise<FeedbackLoopCase[]> {
    return USE_MOCK
      ? delay(MOCK_FEEDBACK_LOOP)
      : get<FeedbackLoopCase[]>("/admin/feedback-loop");
  },
  getReplay(id: string): Promise<ReplayComparison> {
    return USE_MOCK
      ? delay(mockReplay(id), 700)
      : get<ReplayComparison>(`/replay/${id}`);
  },
};

export const queryKeys = {
  overview: ["overview"] as const,
  traces: ["traces"] as const,
  trace: (id: string) => ["trace", id] as const,
  history: ["history"] as const,
  answer: (id: string) => ["answer", id] as const,
  latency: ["latency"] as const,
  cost: ["cost"] as const,
  quality: ["quality"] as const,
  flags: ["flags"] as const,
  guardrails: ["guardrails"] as const,
  users: ["users"] as const,
  user: (id: string) => ["user", id] as const,
  feedbackLoop: ["feedback-loop"] as const,
  replay: (id: string) => ["replay", id] as const,
};
