"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  ExternalLink,
  RotateCcw,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";

import { api, queryKeys } from "@/lib/api";
import type { TraceDetail } from "@/lib/types";
import { RouteBadge, SeverityBadge, StatusBadge } from "@/components/badges";
import { SpanWaterfall } from "@/components/admin/span-waterfall";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

function fmtMs(ms: number) {
  return ms >= 1000
    ? `${(ms / 1000).toFixed(2)} s`
    : `${ms.toLocaleString()} ms`;
}

function Meta({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <div className="label-micro">{label}</div>
      <div className="font-mono text-xs tabular">{value}</div>
    </div>
  );
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-border bg-secondary">
      <div className="border-b border-border px-4 py-2.5">
        <span className="label-micro">{title}</span>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function ProvenanceTab({ trace }: { trace: TraceDetail }) {
  const { request_chunks, sql_execution } = trace;
  if (request_chunks.length === 0 && !sql_execution) {
    return (
      <p className="text-sm text-muted-foreground">
        No provenance recorded for this request.
      </p>
    );
  }
  const used = request_chunks.filter((c) => c.used_in_prompt).length;

  return (
    <div className="space-y-6">
      {request_chunks.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="label-micro">retrieved chunks</span>
            <span className="font-mono text-[11px] text-muted-foreground">
              {request_chunks.length} retrieved · {used} used in prompt
            </span>
          </div>
          <div className="overflow-hidden rounded-md border border-border">
            {request_chunks.map((c) => (
              <div
                key={c.chunk_id}
                className={`flex items-center gap-3 border-b border-border px-3 py-2 last:border-0 ${
                  c.used_in_prompt ? "" : "opacity-50"
                }`}
              >
                <span className="w-6 text-center font-mono text-[11px] text-muted-foreground">
                  {c.rank}
                </span>
                <span
                  className={`w-12 text-right font-mono text-xs tabular ${
                    c.similarity >= 0.5 ? "text-success" : "text-warning"
                  }`}
                >
                  {c.similarity.toFixed(2)}
                </span>
                <span className="min-w-0 flex-1 truncate text-sm">
                  {c.title}
                </span>
                <span className="hidden truncate font-mono text-[11px] text-muted-foreground sm:block sm:max-w-[280px]">
                  {c.chunk_id}
                </span>
                <span className="label-micro tracking-wide">{c.source}</span>
                {c.used_in_prompt ? (
                  <span className="rounded-sm bg-success/15 px-1.5 py-0.5 font-mono text-[10px] uppercase text-success">
                    used
                  </span>
                ) : (
                  <span className="rounded-sm bg-muted px-1.5 py-0.5 font-mono text-[10px] uppercase text-muted-foreground">
                    trimmed
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {sql_execution && (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="label-micro">sql execution</span>
            <span className="font-mono text-[11px] text-muted-foreground">
              {sql_execution.row_count} rows · {sql_execution.execution_ms} ms
              {sql_execution.timed_out ? " · TIMED OUT" : ""}
            </span>
          </div>
          <pre className="overflow-x-auto rounded-md border border-border bg-background/50 p-3 font-mono text-[11px] leading-relaxed">
            {sql_execution.generated_sql}
          </pre>
          {sql_execution.error ? (
            <p className="font-mono text-xs text-danger">
              {sql_execution.error}
            </p>
          ) : sql_execution.result_rows.length > 0 ? (
            <div className="overflow-x-auto rounded-md border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    {Object.keys(sql_execution.result_rows[0]).map((k) => (
                      <th
                        key={k}
                        className="label-micro px-3 py-2 text-left"
                      >
                        {k}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sql_execution.result_rows.map((r, i) => (
                    <tr
                      key={i}
                      className="border-b border-border last:border-0"
                    >
                      {Object.values(r).map((v, j) => (
                        <td
                          key={j}
                          className="px-3 py-2 font-mono text-xs tabular"
                        >
                          {String(v)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

function ScoresTab({ trace }: { trace: TraceDetail }) {
  if (trace.scores.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No quality scores — RAGAS scoring runs only on retrieval-backed
        answers.
      </p>
    );
  }
  return (
    <div className="space-y-4">
      {trace.scores.map((s) => (
        <div key={s.metric} className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs">{s.metric}</span>
            <span className="font-mono text-xs tabular">
              {s.value.toFixed(2)}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-sm bg-background">
            <div
              className={`h-full rounded-sm ${
                s.value >= 0.85
                  ? "bg-success"
                  : s.value >= 0.7
                    ? "bg-warning"
                    : "bg-danger"
              }`}
              style={{ width: `${Math.round(s.value * 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function GuardrailsTab({ trace }: { trace: TraceDetail }) {
  if (trace.guardrails.length === 0) {
    return (
      <div className="flex items-center gap-2 text-sm text-success">
        <ShieldCheck className="size-4" />
        All guardrails passed — nothing triggered.
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {trace.guardrails.map((g) => (
        <div
          key={g.id}
          className="space-y-2 rounded-md border border-border p-3"
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs">{g.rule_name}</span>
            <span className="label-micro tracking-wide">{g.stage}</span>
            <SeverityBadge severity={g.severity} />
            <span className="rounded-sm bg-muted px-1.5 py-0.5 font-mono text-[10px] uppercase text-muted-foreground">
              {g.action}
            </span>
            <span className="font-mono text-[10px] text-muted-foreground">
              {g.implementation === "guardrails_ai"
                ? "Guardrails AI"
                : "hand-rolled"}
            </span>
          </div>
          <p className="text-sm text-muted-foreground">{g.reason}</p>
        </div>
      ))}
    </div>
  );
}

function FlagsTab({ trace }: { trace: TraceDetail }) {
  if (trace.flags.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No flags raised.</p>
    );
  }
  return (
    <div className="space-y-3">
      {trace.flags.map((f) => (
        <div
          key={f.id}
          className="space-y-2 rounded-md border border-border p-3"
        >
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-danger">
              {f.flag_name}
            </span>
            <SeverityBadge severity={f.severity} />
          </div>
          <p className="text-sm text-muted-foreground">{f.description}</p>
        </div>
      ))}
    </div>
  );
}

function FeedbackTab({ trace }: { trace: TraceDetail }) {
  const fb = trace.feedback;
  if (!fb) {
    return (
      <p className="text-sm text-muted-foreground">
        No user feedback submitted.
      </p>
    );
  }
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        {fb.thumbs === "up" ? (
          <ThumbsUp className="size-4 text-success" />
        ) : (
          <ThumbsDown className="size-4 text-danger" />
        )}
        <span className="text-sm capitalize">{fb.thumbs}</span>
      </div>
      {fb.comment && (
        <p className="rounded-md border border-border bg-background/50 p-3 text-sm">
          “{fb.comment}”
        </p>
      )}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-28 w-full rounded-md" />
      <Skeleton className="h-64 w-full rounded-md" />
      <Skeleton className="h-48 w-full rounded-md" />
    </div>
  );
}

export function TraceDetailView({ requestId }: { requestId: string }) {
  const { data: trace, isLoading, isError } = useQuery({
    queryKey: queryKeys.trace(requestId),
    queryFn: () => api.getTraceDetail(requestId),
  });

  if (isLoading) return <LoadingState />;
  if (isError || !trace) {
    return (
      <Panel title="error">
        <p className="text-sm text-danger">
          Could not load trace{" "}
          <span className="font-mono">{requestId}</span>.
        </p>
      </Panel>
    );
  }

  const r = trace.request;
  const totalTokens =
    r.prompt_tokens + r.completion_tokens + r.embedding_tokens;
  const rd = trace.route_decision;

  return (
    <div className="space-y-6">
      <Link
        href="/admin"
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" /> back to traces
      </Link>

      {/* header strip */}
      <div className="reveal space-y-5 rounded-md border border-border bg-secondary p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 space-y-2">
            <div className="flex items-center gap-2">
              <RouteBadge route={r.route} />
              <StatusBadge status={r.final_status} />
              <span className="font-mono text-[11px] text-muted-foreground">
                {new Date(r.created_at).toLocaleString()}
              </span>
            </div>
            <h1 className="font-display text-2xl leading-snug tracking-tight">
              {r.question}
            </h1>
          </div>
          <div className="flex shrink-0 gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link href={`/replay/${r.request_id}`}>
                <RotateCcw className="size-3.5" /> Replay
              </Link>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link href="/">
                <ExternalLink className="size-3.5" /> Public view
              </Link>
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 border-t border-border pt-4 sm:grid-cols-3 lg:grid-cols-6">
          <Meta label="latency" value={fmtMs(r.latency_ms)} />
          <Meta label="total tokens" value={totalTokens.toLocaleString()} />
          <Meta
            label="cost"
            value={`$${r.total_cost_usd.toFixed(4)}`}
          />
          <Meta label="model" value={r.model} />
          <Meta label="prompt ver" value={r.prompt_version} />
          <Meta label="temp" value={r.temperature.toFixed(1)} />
          <Meta
            label="request_id"
            value={<span className="text-muted-foreground">{r.request_id}</span>}
          />
          <Meta
            label="client_id"
            value={<span className="text-muted-foreground">{r.client_id}</span>}
          />
          <Meta
            label="session_id"
            value={
              <span className="text-muted-foreground">{r.session_id}</span>
            }
          />
        </div>
      </div>

      {/* router decision */}
      <div className="reveal flex flex-wrap items-center gap-x-6 gap-y-2 rounded-md border border-border bg-secondary px-4 py-3">
        <span className="label-micro">router</span>
        <span className="font-mono text-xs">
          {rd.category}{" "}
          <span className="text-muted-foreground">
            · confidence {rd.confidence.toFixed(2)} · {rd.router_latency_ms} ms
          </span>
        </span>
        <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
          {rd.reasoning}
        </span>
      </div>

      {/* waterfall */}
      <div className="reveal">
        <SpanWaterfall spans={trace.spans} />
      </div>

      {/* tabs */}
      <div className="reveal rounded-md border border-border bg-secondary">
        <Tabs defaultValue="provenance" className="gap-0">
          <div className="border-b border-border px-2">
            <TabsList className="h-auto bg-transparent p-0">
              {[
                ["provenance", "Provenance"],
                ["scores", "Scores"],
                ["guardrails", "Guardrails"],
                ["flags", "Flags"],
                ["feedback", "Feedback"],
                ["raw", "Raw"],
              ].map(([v, label]) => (
                <TabsTrigger
                  key={v}
                  value={v}
                  className="rounded-none border-b-2 border-transparent px-4 py-3 data-[state=active]:border-primary"
                >
                  {label}
                </TabsTrigger>
              ))}
            </TabsList>
          </div>
          <div className="p-5">
            <TabsContent value="provenance">
              <ProvenanceTab trace={trace} />
            </TabsContent>
            <TabsContent value="scores">
              <ScoresTab trace={trace} />
            </TabsContent>
            <TabsContent value="guardrails">
              <GuardrailsTab trace={trace} />
            </TabsContent>
            <TabsContent value="flags">
              <FlagsTab trace={trace} />
            </TabsContent>
            <TabsContent value="feedback">
              <FeedbackTab trace={trace} />
            </TabsContent>
            <TabsContent value="raw">
              <pre className="max-h-[480px] overflow-auto rounded-md border border-border bg-background/50 p-3 font-mono text-[11px] leading-relaxed">
                {JSON.stringify(trace, null, 2)}
              </pre>
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
}
