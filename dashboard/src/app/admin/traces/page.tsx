"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight, Search } from "lucide-react";

import { api, queryKeys } from "@/lib/api";
import type { FinalStatus, Route } from "@/lib/types";
import { RouteBadge, StatusBadge } from "@/components/badges";
import { PageHeader } from "@/components/admin/primitives";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const ROUTES: (Route | "all")[] = ["all", "narrative", "structured", "both"];
const STATUSES: (FinalStatus | "all")[] = [
  "all",
  "success",
  "flagged",
  "error",
  "refused",
];

export default function TracesExplorerPage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.traces,
    queryFn: () => api.getTraces(),
  });

  const [q, setQ] = useState("");
  const [route, setRoute] = useState<Route | "all">("all");
  const [status, setStatus] = useState<FinalStatus | "all">("all");
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [sort, setSort] = useState<"time" | "latency" | "cost">("time");

  const rows = useMemo(() => {
    let r = data ?? [];
    if (q.trim())
      r = r.filter((t) =>
        t.question.toLowerCase().includes(q.toLowerCase().trim()),
      );
    if (route !== "all") r = r.filter((t) => t.route === route);
    if (status !== "all") r = r.filter((t) => t.final_status === status);
    if (flaggedOnly) r = r.filter((t) => t.flags.length > 0);
    return [...r].sort((a, b) => {
      if (sort === "latency") return b.latency_ms - a.latency_ms;
      if (sort === "cost") return b.total_cost_usd - a.total_cost_usd;
      return b.created_at.localeCompare(a.created_at);
    });
  }, [data, q, route, status, flaggedOnly, sort]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Traces"
        subtitle="Every request across all anonymous users. Click a row for the full trace."
      />

      {/* filter bar */}
      <div className="reveal flex flex-wrap items-center gap-3 rounded-md border border-border bg-secondary p-3">
        <div className="flex min-w-[220px] flex-1 items-center gap-2 rounded-sm border border-border bg-background/40 px-2">
          <Search className="size-3.5 text-muted-foreground" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="search question…"
            className="w-full bg-transparent py-1.5 text-sm outline-none placeholder:text-muted-foreground"
          />
        </div>
        <FilterGroup
          options={ROUTES}
          value={route}
          onChange={(v) => setRoute(v as Route | "all")}
        />
        <FilterGroup
          options={STATUSES}
          value={status}
          onChange={(v) => setStatus(v as FinalStatus | "all")}
        />
        <button
          type="button"
          onClick={() => setFlaggedOnly((v) => !v)}
          className={cn(
            "rounded-sm border px-2.5 py-1 font-mono text-[11px] uppercase tracking-wide transition-colors",
            flaggedOnly
              ? "border-warning/50 bg-warning/10 text-warning"
              : "border-border text-muted-foreground hover:text-foreground",
          )}
        >
          flagged only
        </button>
        <select
          value={sort}
          onChange={(e) =>
            setSort(e.target.value as "time" | "latency" | "cost")
          }
          className="rounded-sm border border-border bg-background/40 px-2 py-1 font-mono text-[11px] outline-none"
        >
          <option value="time">sort: newest</option>
          <option value="latency">sort: latency</option>
          <option value="cost">sort: cost</option>
        </select>
      </div>

      <div className="reveal overflow-hidden rounded-md border border-border bg-secondary">
        <div className="grid grid-cols-[96px_1fr_84px_84px_72px_64px_72px_24px] items-center gap-3 border-b border-border px-4 py-2.5">
          {[
            "request",
            "question",
            "route",
            "status",
            "latency",
            "faith",
            "cost",
            "",
          ].map((h, idx) => (
            <span
              key={idx}
              className={cn("label-micro", idx >= 4 && idx < 7 && "text-right")}
            >
              {h}
            </span>
          ))}
        </div>

        {isLoading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-9 w-full rounded-sm" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted-foreground">
            No traces match these filters.
          </p>
        ) : (
          rows.map((t) => (
            <Link
              key={t.request_id}
              href={`/admin/traces/${t.request_id}`}
              className="grid grid-cols-[96px_1fr_84px_84px_72px_64px_72px_24px] items-center gap-3 border-b border-border px-4 py-3 transition-colors last:border-0 hover:bg-background/50"
            >
              <span className="font-mono text-[11px] text-muted-foreground">
                {t.request_id}
              </span>
              <span className="min-w-0 truncate text-sm">{t.question}</span>
              <RouteBadge route={t.route} />
              <StatusBadge status={t.final_status} />
              <span className="text-right font-mono text-xs tabular">
                {t.latency_ms.toLocaleString()}
              </span>
              <span className="text-right font-mono text-xs tabular">
                {t.faithfulness === null ? "—" : t.faithfulness.toFixed(2)}
              </span>
              <span className="text-right font-mono text-xs tabular text-muted-foreground">
                ${t.total_cost_usd.toFixed(4)}
              </span>
              <ChevronRight className="size-4 justify-self-end text-muted-foreground" />
            </Link>
          ))
        )}
      </div>
      <p className="text-xs text-muted-foreground">
        {rows.length} of {data?.length ?? 0} traces
      </p>
    </div>
  );
}

function FilterGroup({
  options,
  value,
  onChange,
}: {
  options: string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-0.5 rounded-sm border border-border bg-background/40 p-0.5">
      {options.map((o) => (
        <button
          key={o}
          type="button"
          onClick={() => onChange(o)}
          className={cn(
            "rounded-[3px] px-2 py-1 font-mono text-[11px] uppercase tracking-wide transition-colors",
            value === o
              ? "bg-secondary text-foreground"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {o}
        </button>
      ))}
    </div>
  );
}
