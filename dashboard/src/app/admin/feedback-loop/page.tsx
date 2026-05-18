"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, GitCommit } from "lucide-react";

import { api, queryKeys } from "@/lib/api";
import { PageHeader, Panel } from "@/components/admin/primitives";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

function Metric({
  label,
  before,
  after,
  betterUp,
  fmt = (v: number) => `${v}`,
}: {
  label: string;
  before: number;
  after: number;
  betterUp: boolean;
  fmt?: (v: number) => string;
}) {
  const improved = betterUp ? after > before : after < before;
  return (
    <div className="rounded-sm border border-border p-3">
      <div className="label-micro">{label}</div>
      <div className="mt-2 flex items-center gap-2 font-mono text-sm tabular">
        <span className="text-muted-foreground">{fmt(before)}</span>
        <ArrowRight className="size-3 text-muted-foreground" />
        <span className={improved ? "text-success" : "text-danger"}>
          {fmt(after)}
        </span>
      </div>
    </div>
  );
}

export default function FeedbackLoopPage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.feedbackLoop,
    queryFn: () => api.getFeedbackLoop(),
  });
  const [idx, setIdx] = useState(0);

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Feedback loop"
          subtitle="trace → score → flag → debug → fix → retest"
        />
        <Skeleton className="h-64 w-full rounded-md" />
      </div>
    );
  }

  const c = data[idx];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Feedback loop"
        subtitle="The thesis in action: the observability layer caught a real failure, and the fix is measurable."
      />

      <div className="reveal flex flex-wrap gap-2">
        {data.map((cc, i) => (
          <button
            key={cc.id}
            type="button"
            onClick={() => setIdx(i)}
            className={cn(
              "rounded-sm border px-3 py-2 text-left text-xs transition-colors",
              i === idx
                ? "border-primary/50 bg-secondary"
                : "border-border text-muted-foreground hover:text-foreground",
            )}
          >
            {cc.title}
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="before" i={1}>
          <p className="text-sm">{c.before.answer}</p>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <div className="rounded-sm border border-border p-3">
              <div className="label-micro">faithfulness</div>
              <div className="mt-1 readout text-2xl text-danger">
                {c.before.faithfulness.toFixed(2)}
              </div>
            </div>
            <div className="rounded-sm border border-border p-3">
              <div className="label-micro">flags</div>
              <div className="mt-2 flex flex-wrap gap-1">
                {c.before.flags.map((f) => (
                  <span
                    key={f}
                    className="rounded-sm bg-danger/15 px-1.5 py-0.5 font-mono text-[10px] uppercase text-danger"
                  >
                    {f}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </Panel>

        <Panel title="after" i={2}>
          <p className="text-sm">{c.after.answer}</p>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <div className="rounded-sm border border-border p-3">
              <div className="label-micro">faithfulness</div>
              <div className="mt-1 readout text-2xl text-success">
                {c.after.faithfulness.toFixed(2)}
              </div>
            </div>
            <div className="rounded-sm border border-border p-3">
              <div className="label-micro">flags</div>
              <div className="mt-2 text-xs text-success">
                {c.after.flags.length === 0
                  ? "none — resolved"
                  : c.after.flags.join(", ")}
              </div>
            </div>
          </div>
        </Panel>
      </div>

      <Panel title="what changed" i={1}>
        <div className="space-y-4">
          <p className="text-sm">{c.change_note}</p>
          <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
            <GitCommit className="size-3.5" /> fix commit {c.fix_commit}
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Metric
              label="faithfulness"
              before={c.before.faithfulness}
              after={c.after.faithfulness}
              betterUp
              fmt={(v) => v.toFixed(2)}
            />
            <Metric
              label="flags"
              before={c.before.flags.length}
              after={c.after.flags.length}
              betterUp={false}
            />
            <Metric
              label="latency"
              before={c.before.latency_ms}
              after={c.after.latency_ms}
              betterUp={false}
              fmt={(v) => `${v}ms`}
            />
            <Metric
              label="cost"
              before={c.before.cost_usd}
              after={c.after.cost_usd}
              betterUp={false}
              fmt={(v) => `$${v.toFixed(4)}`}
            />
          </div>
          <div className="flex items-center gap-2">
            {c.timeline.map((t, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="rounded-sm border border-border px-2 py-1 text-center">
                  <div className="label-micro">{t.t}</div>
                  <div
                    className={cn(
                      "font-mono text-xs tabular",
                      t.faithfulness >= 0.85
                        ? "text-success"
                        : "text-danger",
                    )}
                  >
                    {t.faithfulness.toFixed(2)}
                  </div>
                </div>
                {i < c.timeline.length - 1 && (
                  <ArrowRight className="size-3 text-muted-foreground" />
                )}
              </div>
            ))}
          </div>
        </div>
      </Panel>
    </div>
  );
}
