"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, RefreshCw } from "lucide-react";

import { api, queryKeys } from "@/lib/api";
import type { ReplayRun } from "@/lib/types";
import { RouteBadge } from "@/components/badges";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

function RunCard({
  run,
  tone,
}: {
  run: ReplayRun;
  tone: "original" | "replay";
}) {
  return (
    <div className="space-y-4 rounded-md border border-border bg-secondary p-5">
      <div className="flex items-center justify-between">
        <span className="label-micro">
          {tone === "original" ? "original" : "replay"} · {run.prompt_version}
        </span>
        <RouteBadge route={run.route} />
      </div>
      <p className="text-sm leading-7">{run.answer}</p>
      <div className="grid grid-cols-3 gap-2 border-t border-border pt-4">
        <div>
          <div className="label-micro">latency</div>
          <div className="mt-1 font-mono text-xs tabular">
            {run.latency_ms.toLocaleString()} ms
          </div>
        </div>
        <div>
          <div className="label-micro">tokens</div>
          <div className="mt-1 font-mono text-xs tabular">
            {run.total_tokens.toLocaleString()}
          </div>
        </div>
        <div>
          <div className="label-micro">faithfulness</div>
          <div
            className={cn(
              "mt-1 font-mono text-xs tabular",
              run.faithfulness === null
                ? "text-muted-foreground"
                : run.faithfulness >= 0.85
                  ? "text-success"
                  : "text-warning",
            )}
          >
            {run.faithfulness === null ? "—" : run.faithfulness.toFixed(2)}
          </div>
        </div>
      </div>
    </div>
  );
}

export function ReplayView({ requestId }: { requestId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.replay(requestId),
    queryFn: () => api.getReplay(requestId),
  });

  if (isLoading || !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48 rounded-sm" />
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-72 rounded-md" />
          <Skeleton className="h-72 rounded-md" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Link
        href={`/answer/${requestId}`}
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" /> back to answer
      </Link>

      <div className="reveal flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <span className="label-micro">replay · prompt-version compare</span>
          <h1 className="font-display text-2xl leading-snug tracking-tight">
            {data.question}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <select
            defaultValue="v2"
            className="rounded-sm border border-border bg-secondary px-2 py-1.5 font-mono text-xs outline-none"
          >
            <option value="v2">v2 — stricter grounding</option>
            <option value="v3">v3 — concise</option>
          </select>
          <Button
            size="sm"
            onClick={() => toast("Re-run is wired with the backend.")}
          >
            <RefreshCw className="size-3.5" /> Re-run
          </Button>
        </div>
      </div>

      <div className="reveal grid gap-6 lg:grid-cols-2">
        <RunCard run={data.original} tone="original" />
        <RunCard run={data.replay} tone="replay" />
      </div>

      <p className="text-xs text-muted-foreground">
        Replays don&apos;t overwrite history — they&apos;re saved as linked
        runs (`replay_of_request_id`).
      </p>
    </div>
  );
}
