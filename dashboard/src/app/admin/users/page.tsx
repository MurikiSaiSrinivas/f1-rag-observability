"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight } from "lucide-react";

import { api, queryKeys } from "@/lib/api";
import { PageHeader } from "@/components/admin/primitives";
import { Skeleton } from "@/components/ui/skeleton";
import { ROUTE_COLOR } from "@/components/admin/primitives";

export default function UsersPage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.users,
    queryFn: () => api.getUsers(),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Users"
        subtitle="Anonymous browser identities — no accounts. Cleared cookies = new identity."
      />

      <div className="reveal overflow-hidden rounded-md border border-border bg-secondary">
        <div className="grid grid-cols-[110px_1fr_70px_90px_80px_70px_70px_24px] items-center gap-3 border-b border-border px-4 py-2.5">
          {[
            "client_id",
            "route mix",
            "reqs",
            "faith",
            "feedback",
            "cost",
            "flagged",
            "",
          ].map((h, i) => (
            <span key={i} className="label-micro">
              {h}
            </span>
          ))}
        </div>

        {isLoading || !data ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full rounded-sm" />
            ))}
          </div>
        ) : (
          data.map((u) => {
            const totalMix =
              u.route_mix.narrative +
                u.route_mix.structured +
                u.route_mix.both || 1;
            return (
              <Link
                key={u.client_id}
                href={`/admin/users/${u.client_id}`}
                className="grid grid-cols-[110px_1fr_70px_90px_80px_70px_70px_24px] items-center gap-3 border-b border-border px-4 py-3 transition-colors last:border-0 hover:bg-background/50"
              >
                <span className="font-mono text-[11px] text-muted-foreground">
                  {u.client_id}
                </span>
                <div className="flex h-2 overflow-hidden rounded-sm">
                  {(["narrative", "structured", "both"] as const).map((r) => (
                    <span
                      key={r}
                      style={{
                        width: `${(u.route_mix[r] / totalMix) * 100}%`,
                        background: ROUTE_COLOR[r],
                      }}
                    />
                  ))}
                </div>
                <span className="font-mono text-xs tabular">
                  {u.request_count}
                </span>
                <span className="font-mono text-xs tabular">
                  {u.avg_faithfulness === null
                    ? "—"
                    : u.avg_faithfulness.toFixed(2)}
                </span>
                <span className="font-mono text-xs tabular">
                  {Math.round(u.feedback_ratio * 100)}%
                </span>
                <span className="font-mono text-xs tabular text-muted-foreground">
                  ${u.total_cost_usd.toFixed(2)}
                </span>
                <span className="font-mono text-xs tabular text-danger">
                  {u.flagged_count}
                </span>
                <ChevronRight className="size-4 justify-self-end text-muted-foreground" />
              </Link>
            );
          })
        )}
      </div>
    </div>
  );
}
