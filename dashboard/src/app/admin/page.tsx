"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { api, queryKeys } from "@/lib/api";
import { RouteBadge, StatusBadge } from "@/components/badges";
import {
  Bars,
  Columns,
  Donut,
  PageHeader,
  Panel,
  StatTile,
  ROUTE_COLOR,
} from "@/components/admin/primitives";
import { Skeleton } from "@/components/ui/skeleton";

export default function OverviewPage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.overview,
    queryFn: () => api.getOverview(),
  });

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <PageHeader title="Overview" subtitle="System health at a glance." />
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-md" />
          ))}
        </div>
        <Skeleton className="h-64 w-full rounded-md" />
      </div>
    );
  }

  const k = data.kpis;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Overview"
        subtitle="Every request across all anonymous users — last 24h."
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
        <StatTile
          i={1}
          label="requests"
          value={k.total_requests.toLocaleString()}
          unit="24h"
        />
        <StatTile
          i={2}
          label="error rate"
          value={`${(k.error_rate * 100).toFixed(1)}`}
          unit="%"
          delta={k.error_rate < 0.05 ? "within budget" : "elevated"}
          deltaTone={k.error_rate < 0.05 ? "up" : "down"}
        />
        <StatTile
          i={3}
          label="avg latency"
          value={k.avg_latency_ms.toLocaleString()}
          unit="ms"
        />
        <StatTile
          i={4}
          label="cost today"
          value={`$${k.cost_today_usd.toFixed(2)}`}
        />
        <StatTile
          i={5}
          label="avg faithfulness"
          value={k.avg_faithfulness.toFixed(2)}
        />
        <StatTile
          i={6}
          label="feedback ratio"
          value={`${Math.round(k.feedback_ratio * 100)}`}
          unit="% 👍"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Panel title="requests over time" className="lg:col-span-2" i={1}>
          <Columns
            data={data.requests_over_time.map((d) => ({
              label: d.t,
              value: d.requests,
              sub: `${d.requests} req · ${d.errors} err`,
            }))}
            color="var(--primary)"
          />
        </Panel>
        <Panel title="route distribution" i={2}>
          <Donut
            segments={data.route_distribution.map((r) => ({
              label: r.route,
              value: r.count,
              color: ROUTE_COLOR[r.route],
            }))}
          />
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Panel title="top flags firing" i={1}>
          <Bars
            items={data.top_flags.map((f) => ({
              label: f.flag_name,
              value: f.count,
              color: "var(--danger)",
            }))}
          />
        </Panel>

        <Panel title="recent requests" className="lg:col-span-2" i={2}>
          <div className="divide-y divide-border">
            {data.recent.slice(0, 6).map((t) => (
              <Link
                key={t.request_id}
                href={`/admin/traces/${t.request_id}`}
                className="-mx-4 flex items-center gap-3 px-4 py-2 transition-colors hover:bg-background/50"
              >
                <span className="font-mono text-[11px] text-muted-foreground">
                  {new Date(t.created_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
                <span className="min-w-0 flex-1 truncate text-sm">
                  {t.question}
                </span>
                <RouteBadge route={t.route} />
                <StatusBadge status={t.final_status} />
                <span className="w-16 text-right font-mono text-xs tabular text-muted-foreground">
                  {t.latency_ms.toLocaleString()}ms
                </span>
              </Link>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
