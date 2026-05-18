"use client";

import { useQuery } from "@tanstack/react-query";

import { api, queryKeys } from "@/lib/api";
import type { GuardrailStage } from "@/lib/types";
import { SeverityBadge } from "@/components/badges";
import {
  LineChart,
  PageHeader,
  Panel,
  Sparkline,
} from "@/components/admin/primitives";
import { Skeleton } from "@/components/ui/skeleton";

const STAGES: GuardrailStage[] = ["input", "retrieval", "output"];

export default function GuardrailsPage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.guardrails,
    queryFn: () => api.getGuardrails(),
  });

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <PageHeader title="Guardrails" subtitle="What fired, where, how often." />
        <Skeleton className="h-64 w-full rounded-md" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Guardrails"
        subtitle="~10 hand-rolled rules + one Guardrails AI rule (pii_in_question)."
      />

      <Panel title="triggers by stage over time" i={1}>
        <LineChart
          labels={data.by_stage.map((d) => d.t)}
          series={[
            {
              name: "input",
              points: data.by_stage.map((d) => d.input),
              color: "var(--span-guardrail)",
            },
            {
              name: "retrieval",
              points: data.by_stage.map((d) => d.retrieval),
              color: "var(--span-retrieval)",
            },
            {
              name: "output",
              points: data.by_stage.map((d) => d.output),
              color: "var(--danger)",
            },
          ]}
        />
      </Panel>

      <div className="grid gap-6 lg:grid-cols-3">
        {STAGES.map((stage, si) => (
          <Panel key={stage} title={`${stage} stage`} i={si + 1}>
            <div className="space-y-2">
              {data.rules
                .filter((r) => r.stage === stage)
                .map((r) => (
                  <div
                    key={r.rule_name}
                    className="rounded-sm border border-border p-2.5"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-mono text-xs">
                        {r.rule_name}
                      </span>
                      <span className="font-mono text-xs tabular text-muted-foreground">
                        {r.count}
                      </span>
                    </div>
                    <div className="my-1.5">
                      <Sparkline
                        data={r.trend}
                        color="var(--muted-foreground)"
                        className="h-4"
                      />
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <SeverityBadge severity={r.severity} />
                      <span className="rounded-sm bg-muted px-1.5 py-0.5 font-mono text-[10px] uppercase text-muted-foreground">
                        {r.action}
                      </span>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {r.implementation === "guardrails_ai"
                          ? "Guardrails AI"
                          : "hand-rolled"}
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          </Panel>
        ))}
      </div>
    </div>
  );
}
