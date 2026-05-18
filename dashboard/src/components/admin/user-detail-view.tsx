"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";

import { api, queryKeys } from "@/lib/api";
import { RouteBadge, StatusBadge } from "@/components/badges";
import { Panel, StatTile } from "@/components/admin/primitives";
import { Skeleton } from "@/components/ui/skeleton";

export function UserDetailView({ clientId }: { clientId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.user(clientId),
    queryFn: () => api.getUser(clientId),
  });

  if (isLoading || !data) {
    return <Skeleton className="h-64 w-full rounded-md" />;
  }

  const u = data.client;

  return (
    <div className="space-y-6">
      <Link
        href="/admin/users"
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" /> all users
      </Link>

      <div className="reveal space-y-1">
        <h1 className="font-display text-3xl tracking-tight">
          {u.client_id}
        </h1>
        <p className="font-mono text-xs text-muted-foreground">
          first seen {new Date(u.first_seen_at).toLocaleString()} · last seen{" "}
          {new Date(u.last_seen_at).toLocaleString()}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <StatTile i={1} label="requests" value={`${u.request_count}`} />
        <StatTile
          i={2}
          label="avg faithfulness"
          value={
            u.avg_faithfulness === null ? "—" : u.avg_faithfulness.toFixed(2)
          }
        />
        <StatTile
          i={3}
          label="feedback"
          value={`${Math.round(u.feedback_ratio * 100)}`}
          unit="% 👍"
        />
        <StatTile
          i={4}
          label="cost"
          value={`$${u.total_cost_usd.toFixed(2)}`}
        />
        <StatTile
          i={5}
          label="flagged"
          value={`${u.flagged_count}`}
        />
      </div>

      <Panel title="question history" i={1}>
        <div className="divide-y divide-border">
          {data.history.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No requests recorded for this client.
            </p>
          ) : (
            data.history.map((t) => (
              <Link
                key={t.request_id}
                href={`/admin/traces/${t.request_id}`}
                className="-mx-4 flex items-center gap-3 px-4 py-2.5 transition-colors hover:bg-background/50"
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
              </Link>
            ))
          )}
        </div>
      </Panel>
    </div>
  );
}
