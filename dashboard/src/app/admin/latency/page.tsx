"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { api, queryKeys } from "@/lib/api";
import { RouteBadge } from "@/components/badges";
import {
  Bars,
  LineChart,
  PageHeader,
  Panel,
  StatTile,
  SPAN_COLOR,
} from "@/components/admin/primitives";
import { Skeleton } from "@/components/ui/skeleton";

export default function LatencyPage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.latency,
    queryFn: () => api.getLatency(),
  });

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <PageHeader title="Latency" subtitle="Where the time goes." />
        <Skeleton className="h-64 w-full rounded-md" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Latency"
        subtitle="End-to-end percentiles and per-span breakdown."
      />

      <div className="grid grid-cols-3 gap-3">
        <StatTile i={1} label="p50" value={data.p50_ms.toLocaleString()} unit="ms" />
        <StatTile i={2} label="p95" value={data.p95_ms.toLocaleString()} unit="ms" />
        <StatTile i={3} label="p99" value={data.p99_ms.toLocaleString()} unit="ms" />
      </div>

      <Panel title="latency percentiles over time" i={1}>
        <LineChart
          labels={data.trend.map((d) => d.t)}
          series={[
            {
              name: "p50",
              points: data.trend.map((d) => d.p50),
              color: "var(--span-retrieval)",
            },
            {
              name: "p95",
              points: data.trend.map((d) => d.p95),
              color: "var(--warning)",
            },
            {
              name: "p99",
              points: data.trend.map((d) => d.p99),
              color: "var(--danger)",
            },
          ]}
        />
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="average latency by span type" i={1}>
          <Bars
            items={data.by_span.map((s) => ({
              label: s.span_type,
              value: s.avg_ms,
              sub: `${s.avg_ms} ms · ${s.pct}%`,
              color: SPAN_COLOR[s.span_type],
            }))}
          />
        </Panel>

        <Panel title="slowest requests" i={2}>
          <div className="divide-y divide-border">
            {data.slowest.map((s) => (
              <Link
                key={s.request_id}
                href={`/admin/traces/${s.request_id}`}
                className="-mx-4 flex items-center gap-3 px-4 py-2.5 transition-colors hover:bg-background/50"
              >
                <span className="min-w-0 flex-1 truncate text-sm">
                  {s.question}
                </span>
                <RouteBadge route={s.route} />
                <span className="font-mono text-[11px] text-muted-foreground">
                  {s.dominant_span}
                </span>
                <span className="w-16 text-right font-mono text-xs tabular text-danger">
                  {s.latency_ms.toLocaleString()}ms
                </span>
              </Link>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
