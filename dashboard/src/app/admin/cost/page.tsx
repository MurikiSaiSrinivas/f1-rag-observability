"use client";

import { useQuery } from "@tanstack/react-query";

import { api, queryKeys } from "@/lib/api";
import {
  Bars,
  Columns,
  LineChart,
  PageHeader,
  Panel,
  StatTile,
  ROUTE_COLOR,
} from "@/components/admin/primitives";
import { Skeleton } from "@/components/ui/skeleton";

export default function CostPage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.cost,
    queryFn: () => api.getCost(),
  });

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <PageHeader title="Cost" subtitle="Spend, tracked as if billed." />
        <Skeleton className="h-64 w-full rounded-md" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Cost"
        subtitle="Tracked as if billed — the project runs on the free OpenAI token program."
      />

      <div className="grid grid-cols-3 gap-3">
        <StatTile i={1} label="today" value={`$${data.today_usd.toFixed(2)}`} />
        <StatTile i={2} label="this week" value={`$${data.week_usd.toFixed(2)}`} />
        <StatTile
          i={3}
          label="this month"
          value={`$${data.month_usd.toFixed(2)}`}
        />
      </div>

      <Panel title="cumulative spend" i={1}>
        <LineChart
          labels={data.cumulative.map((d) => d.t)}
          series={[
            {
              name: "usd",
              points: data.cumulative.map((d) => d.usd),
              color: "var(--primary)",
            },
          ]}
        />
      </Panel>

      <div className="grid gap-6 lg:grid-cols-3">
        <Panel title="by model" i={1}>
          <Bars
            items={data.by_model.map((m) => ({
              label: m.model,
              value: m.usd,
              sub: `$${m.usd.toFixed(2)}`,
            }))}
          />
        </Panel>
        <Panel title="by route" i={2}>
          <Bars
            items={data.by_route.map((r) => ({
              label: r.route,
              value: r.usd,
              sub: `$${r.usd.toFixed(2)}`,
              color: ROUTE_COLOR[r.route],
            }))}
          />
        </Panel>
        <Panel title="by operation" i={3}>
          <Bars
            items={data.by_operation.map((o) => ({
              label: o.operation,
              value: o.usd,
              sub: `$${o.usd.toFixed(2)}`,
            }))}
          />
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel
          title="per-request cost distribution"
          right={
            <span className="font-mono text-[11px] text-muted-foreground">
              threshold ${data.threshold_usd}
            </span>
          }
          i={1}
        >
          <Columns
            data={data.per_request.map((b) => ({
              label: b.bucket,
              value: b.count,
            }))}
            color="var(--span-llm)"
          />
        </Panel>

        <Panel title="token usage" i={2}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                {["day", "prompt", "completion", "total"].map((h) => (
                  <th
                    key={h}
                    className="label-micro px-2 py-2 text-left first:pl-0 last:text-right"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.tokens.map((t) => (
                <tr key={t.day} className="border-b border-border last:border-0">
                  <td className="px-2 py-2 pl-0 font-mono text-xs">{t.day}</td>
                  <td className="px-2 py-2 font-mono text-xs tabular">
                    {t.prompt.toLocaleString()}
                  </td>
                  <td className="px-2 py-2 font-mono text-xs tabular">
                    {t.completion.toLocaleString()}
                  </td>
                  <td className="px-2 py-2 text-right font-mono text-xs tabular">
                    {t.total.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </div>
  );
}
