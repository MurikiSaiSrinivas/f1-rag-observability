"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { api, queryKeys } from "@/lib/api";
import {
  Columns,
  LineChart,
  PageHeader,
  Panel,
  StatTile,
} from "@/components/admin/primitives";
import { Skeleton } from "@/components/ui/skeleton";

export default function QualityPage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.quality,
    queryFn: () => api.getQuality(),
  });

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <PageHeader title="Quality" subtitle="RAGAS answer scoring." />
        <Skeleton className="h-64 w-full rounded-md" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Quality"
        subtitle="RAGAS faithfulness & relevance — distributions and trend."
      />

      <div className="grid grid-cols-3 gap-3">
        {data.distributions.map((d, i) => (
          <StatTile
            key={d.metric}
            i={i + 1}
            label={`${d.metric} (mean)`}
            value={d.mean.toFixed(2)}
          />
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {data.distributions.map((d, i) => (
          <Panel key={d.metric} title={d.metric} i={i + 1}>
            <Columns
              data={d.buckets.map((b) => ({
                label: b.range,
                value: b.count,
              }))}
              color="var(--span-retrieval)"
            />
          </Panel>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel
          title="score trend"
          right={
            <span className="font-mono text-[11px] text-muted-foreground">
              ▲ {data.prompt_markers.map((m) => `${m.version}@${m.t}`).join(", ")}
            </span>
          }
          i={1}
        >
          <LineChart
            labels={data.trend.map((d) => d.t)}
            series={[
              {
                name: "faithfulness",
                points: data.trend.map((d) => d.faithfulness),
                color: "var(--primary)",
              },
              {
                name: "answer_relevancy",
                points: data.trend.map((d) => d.answer_relevancy),
                color: "var(--span-sql)",
              },
            ]}
          />
        </Panel>

        <Panel title="faithfulness vs. user feedback" i={2}>
          <div className="space-y-3">
            <div className="relative h-32 rounded-sm border border-border bg-background/40">
              {data.scatter.map((p, i) => (
                <span
                  key={i}
                  className="absolute size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full"
                  style={{
                    left: `${p.faithfulness * 100}%`,
                    top:
                      p.feedback === "up"
                        ? "25%"
                        : p.feedback === "down"
                          ? "75%"
                          : "50%",
                    background:
                      p.feedback === "up"
                        ? "var(--success)"
                        : p.feedback === "down"
                          ? "var(--danger)"
                          : "var(--muted-foreground)",
                  }}
                />
              ))}
            </div>
            <div className="flex justify-between font-mono text-[10px] text-muted-foreground">
              <span>faithfulness 0.0</span>
              <span>1.0</span>
            </div>
            <p className="text-xs text-muted-foreground">
              👍 top band · 👎 bottom band — low-faithfulness 👍 or
              high-faithfulness 👎 points signal scorer/user disagreement.
            </p>
          </div>
        </Panel>
      </div>

      <Panel title="lowest-faithfulness recent answers" i={1}>
        <div className="divide-y divide-border">
          {data.lowest.map((l) => (
            <Link
              key={l.request_id}
              href={`/admin/traces/${l.request_id}`}
              className="-mx-4 flex items-center gap-3 px-4 py-2.5 transition-colors hover:bg-background/50"
            >
              <span className="min-w-0 flex-1 truncate text-sm">
                {l.question}
              </span>
              <span className="font-mono text-xs tabular text-danger">
                {l.faithfulness.toFixed(2)}
              </span>
            </Link>
          ))}
        </div>
      </Panel>
    </div>
  );
}
