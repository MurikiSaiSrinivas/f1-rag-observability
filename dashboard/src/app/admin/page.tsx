"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight } from "lucide-react";

import { api, queryKeys } from "@/lib/api";
import { RouteBadge, StatusBadge } from "@/components/badges";
import { Skeleton } from "@/components/ui/skeleton";

export default function AdminTracesIndex() {
  const { data: traces, isLoading } = useQuery({
    queryKey: queryKeys.traces,
    queryFn: () => api.getTraces(),
  });

  return (
    <div className="space-y-6">
      <header className="reveal space-y-1">
        <h1 className="font-display text-3xl tracking-tight">Recent traces</h1>
        <p className="text-sm text-muted-foreground">
          Every request across all anonymous users. Click a row to open the
          full trace.
        </p>
      </header>

      <div className="reveal overflow-hidden rounded-md border border-border bg-secondary">
        <div className="grid grid-cols-[110px_1fr_90px_90px_80px_80px_28px] items-center gap-3 border-b border-border px-4 py-2.5">
          {[
            "request_id",
            "question",
            "route",
            "status",
            "latency",
            "faith",
            "",
          ].map((h, i) => (
            <span
              key={i}
              className={`label-micro ${
                i >= 4 ? "text-right" : ""
              }`}
            >
              {h}
            </span>
          ))}
        </div>

        {isLoading ? (
          <div className="space-y-2 p-4">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-9 w-full rounded-sm" />
            ))}
          </div>
        ) : (
          (traces ?? []).map((t) => (
            <Link
              key={t.request_id}
              href={`/admin/traces/${t.request_id}`}
              className="grid grid-cols-[110px_1fr_90px_90px_80px_80px_28px] items-center gap-3 border-b border-border px-4 py-3 transition-colors last:border-0 hover:bg-background/50"
            >
              <span className="font-mono text-[11px] text-muted-foreground">
                {t.request_id}
              </span>
              <span className="min-w-0 truncate text-sm">{t.question}</span>
              <RouteBadge route={t.route} />
              <StatusBadge status={t.final_status} />
              <span className="text-right font-mono text-xs tabular">
                {t.latency_ms.toLocaleString()} ms
              </span>
              <span className="text-right font-mono text-xs tabular">
                {t.faithfulness === null ? "—" : t.faithfulness.toFixed(2)}
              </span>
              <ChevronRight className="size-4 justify-self-end text-muted-foreground" />
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
