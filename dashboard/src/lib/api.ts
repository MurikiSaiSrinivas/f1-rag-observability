/**
 * The single swap point between mock data and the real FastAPI backend.
 *
 * Today: USE_MOCK is true -> typed fixtures from src/lib/mock.ts.
 * Phase 4: set NEXT_PUBLIC_API_BASE and flip USE_MOCK -> these same function
 * signatures fetch the real endpoints. No component or type changes.
 */
import {
  askMock,
  MOCK_HISTORY,
  MOCK_OVERVIEW,
  MOCK_TRACES,
  mockAnswerView,
  mockTraceDetail,
} from "@/lib/mock";
import type {
  AdminOverview,
  AnswerView,
  AskResult,
  HistoryItem,
  TraceDetail,
  TraceRow,
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
};

export const queryKeys = {
  overview: ["overview"] as const,
  traces: ["traces"] as const,
  trace: (id: string) => ["trace", id] as const,
  history: ["history"] as const,
  answer: (id: string) => ["answer", id] as const,
};
