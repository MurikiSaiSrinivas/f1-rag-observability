"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { api, queryKeys } from "@/lib/api";
import { RouteBadge } from "@/components/badges";
import {
  PageHeader,
  Panel,
  Sparkline,
} from "@/components/admin/primitives";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export default function FlagsPage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.flags,
    queryFn: () => api.getFlags(),
  });
  const [active, setActive] = useState<string | null>(null);

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <PageHeader title="Flags / Bad Answers" subtitle="The debugging surface." />
        <Skeleton className="h-64 w-full rounded-md" />
      </div>
    );
  }

  const flagged = active
    ? data.flagged.filter((f) => f.flags.includes(active))
    : data.flagged;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Flags / Bad Answers"
        subtitle="Every flagged request with what you need to debug it — requirement #7."
      />

      <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
        <Panel title="flag rules" i={1}>
          <div className="space-y-1">
            {data.rules.map((r) => (
              <button
                key={r.flag_name}
                type="button"
                onClick={() =>
                  setActive((a) => (a === r.flag_name ? null : r.flag_name))
                }
                className={cn(
                  "w-full rounded-sm border px-3 py-2 text-left transition-colors",
                  active === r.flag_name
                    ? "border-primary/50 bg-background/60"
                    : "border-transparent hover:bg-background/40",
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs">{r.flag_name}</span>
                  <span className="font-mono text-xs tabular text-muted-foreground">
                    {r.count}
                  </span>
                </div>
                <div className="mt-1.5">
                  <Sparkline
                    data={r.trend}
                    color={
                      r.severity === "critical"
                        ? "var(--danger)"
                        : r.severity === "warning"
                          ? "var(--warning)"
                          : "var(--muted-foreground)"
                    }
                    className="h-5"
                  />
                </div>
              </button>
            ))}
          </div>
        </Panel>

        <Panel
          title={active ? `flagged · ${active}` : "all flagged requests"}
          right={
            active && (
              <button
                type="button"
                onClick={() => setActive(null)}
                className="font-mono text-[11px] text-muted-foreground hover:text-foreground"
              >
                clear
              </button>
            )
          }
          i={2}
        >
          <div className="divide-y divide-border">
            {flagged.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No flagged requests for this filter.
              </p>
            ) : (
              flagged.map((t) => (
                <Link
                  key={t.request_id}
                  href={`/admin/traces/${t.request_id}`}
                  className="-mx-4 block px-4 py-3 transition-colors hover:bg-background/50"
                >
                  <div className="flex items-center gap-3">
                    <span className="min-w-0 flex-1 truncate text-sm">
                      {t.question}
                    </span>
                    <RouteBadge route={t.route} />
                    {t.faithfulness !== null && (
                      <span className="font-mono text-xs tabular text-danger">
                        {t.faithfulness.toFixed(2)}
                      </span>
                    )}
                  </div>
                  <div className="mt-1.5 flex items-center gap-2">
                    {t.flags.map((f) => (
                      <span
                        key={f}
                        className="rounded-sm bg-danger/15 px-1.5 py-0.5 font-mono text-[10px] uppercase text-danger"
                      >
                        {f}
                      </span>
                    ))}
                    <span className="truncate text-xs text-muted-foreground">
                      {t.flag_reason}
                    </span>
                  </div>
                </Link>
              ))
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}
