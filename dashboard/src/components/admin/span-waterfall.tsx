"use client";

import { useMemo, useState } from "react";

import { cn } from "@/lib/utils";
import type { Span, SpanType } from "@/lib/types";

const SPAN_BG: Record<SpanType, string> = {
  guardrail: "bg-span-guardrail",
  llm: "bg-span-llm",
  retrieval: "bg-span-retrieval",
  sql: "bg-span-sql",
  orchestration: "bg-span-orchestration",
};

const SPAN_DOT: Record<SpanType, string> = {
  guardrail: "bg-span-guardrail",
  llm: "bg-span-llm",
  retrieval: "bg-span-retrieval",
  sql: "bg-span-sql",
  orchestration: "bg-span-orchestration",
};

function fmt(ms: number) {
  return ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${ms}ms`;
}

export function SpanWaterfall({ spans }: { spans: Span[] }) {
  const byId = useMemo(
    () => new Map(spans.map((s) => [s.span_id, s])),
    [spans],
  );
  const root = spans.find((s) => s.parent_span_id === null);
  const total = root?.duration_ms ?? Math.max(...spans.map((s) => s.end_ts), 1);

  const [selectedId, setSelectedId] = useState<string>(
    root?.span_id ?? spans[0]?.span_id,
  );
  const selected = byId.get(selectedId) ?? root;

  function depth(s: Span) {
    let d = 0;
    let cur: Span | undefined = s;
    while (cur && cur.parent_span_id) {
      d++;
      cur = byId.get(cur.parent_span_id);
    }
    return d;
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
      {/* waterfall */}
      <div className="overflow-hidden rounded-md border border-border bg-secondary">
        <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
          <span className="label-micro">span waterfall</span>
          <span className="font-mono text-[11px] text-muted-foreground tabular">
            total {fmt(total)} · {spans.length} spans
          </span>
        </div>

        <div className="divide-y divide-border">
          {spans.map((s) => {
            const left = (s.start_ts / total) * 100;
            const width = Math.max((s.duration_ms / total) * 100, 0.6);
            const isSel = s.span_id === selectedId;
            return (
              <button
                key={s.span_id}
                type="button"
                onClick={() => setSelectedId(s.span_id)}
                className={cn(
                  "flex w-full items-center gap-3 px-4 py-2 text-left transition-colors hover:bg-background/40",
                  isSel && "bg-background/60",
                )}
              >
                <div
                  className="flex min-w-0 items-center gap-2"
                  style={{
                    width: "44%",
                    paddingLeft: `${depth(s) * 14}px`,
                  }}
                >
                  <span
                    className={cn(
                      "size-2 shrink-0 rounded-[2px]",
                      SPAN_DOT[s.span_type],
                    )}
                  />
                  <span className="truncate font-mono text-xs">{s.name}</span>
                  {s.status === "error" && (
                    <span className="size-1.5 shrink-0 rounded-full bg-danger" />
                  )}
                </div>

                <div className="relative h-5 flex-1">
                  <div
                    className={cn(
                      "absolute top-0 h-5 rounded-[3px] transition-all",
                      SPAN_BG[s.span_type],
                      isSel && "ring-2 ring-primary ring-offset-1 ring-offset-secondary",
                      s.status === "error" && "outline outline-1 outline-danger",
                    )}
                    style={{ left: `${left}%`, width: `${width}%` }}
                    title={`${s.name} — ${fmt(s.duration_ms)}`}
                  />
                </div>

                <span className="w-16 shrink-0 text-right font-mono text-[11px] text-muted-foreground tabular">
                  {fmt(s.duration_ms)}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* inspector */}
      <div className="rounded-md border border-border bg-secondary">
        <div className="border-b border-border px-4 py-2.5">
          <span className="label-micro">span detail</span>
        </div>
        {selected ? (
          <div className="space-y-4 p-4">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "size-2.5 rounded-[2px]",
                  SPAN_DOT[selected.span_type],
                )}
              />
              <span className="font-mono text-sm">{selected.name}</span>
            </div>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 font-mono text-[11px]">
              <dt className="text-muted-foreground">type</dt>
              <dd className="text-right tabular">{selected.span_type}</dd>
              <dt className="text-muted-foreground">status</dt>
              <dd
                className={cn(
                  "text-right",
                  selected.status === "error" ? "text-danger" : "text-success",
                )}
              >
                {selected.status}
              </dd>
              <dt className="text-muted-foreground">start</dt>
              <dd className="text-right tabular">{fmt(selected.start_ts)}</dd>
              <dt className="text-muted-foreground">duration</dt>
              <dd className="text-right tabular">
                {fmt(selected.duration_ms)}
              </dd>
            </dl>
            {Object.keys(selected.attributes).length > 0 && (
              <div>
                <span className="label-micro">attributes</span>
                <pre className="mt-2 overflow-x-auto rounded-sm border border-border bg-background/50 p-2.5 font-mono text-[11px] leading-relaxed">
                  {JSON.stringify(selected.attributes, null, 2)}
                </pre>
              </div>
            )}
          </div>
        ) : (
          <div className="p-4 text-sm text-muted-foreground">
            Select a span.
          </div>
        )}
      </div>
    </div>
  );
}
