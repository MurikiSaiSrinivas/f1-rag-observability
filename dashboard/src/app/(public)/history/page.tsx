"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight, Search, ThumbsDown, ThumbsUp } from "lucide-react";

import { api, queryKeys } from "@/lib/api";
import { RouteBadge } from "@/components/badges";
import { Skeleton } from "@/components/ui/skeleton";

export default function HistoryPage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.history,
    queryFn: () => api.getHistory(),
  });
  const [q, setQ] = useState("");

  const rows = useMemo(() => {
    const r = data ?? [];
    const filtered = q.trim()
      ? r.filter((h) =>
          h.question.toLowerCase().includes(q.toLowerCase().trim()),
        )
      : r;
    return [...filtered].sort((a, b) =>
      b.created_at.localeCompare(a.created_at),
    );
  }, [data, q]);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header className="reveal space-y-1">
        <h1 className="font-display text-3xl tracking-tight">My questions</h1>
        <p className="text-sm text-muted-foreground">
          Saved to this browser only. Click any to revisit the answer and its
          sources.
        </p>
      </header>

      <div className="reveal flex items-center gap-2 rounded-md border border-border bg-secondary px-3">
        <Search className="size-4 text-muted-foreground" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="filter your questions…"
          className="w-full bg-transparent py-2.5 text-sm outline-none placeholder:text-muted-foreground"
        />
      </div>

      <div className="reveal overflow-hidden rounded-md border border-border bg-secondary">
        {isLoading || !data ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full rounded-sm" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <p className="p-10 text-center text-sm text-muted-foreground">
            {q
              ? "Nothing matches that filter."
              : "You haven't asked anything yet."}
          </p>
        ) : (
          rows.map((h) => (
            <Link
              key={h.request_id}
              href={`/answer/${h.request_id}`}
              className="flex items-center gap-3 border-b border-border px-4 py-3 transition-colors last:border-0 hover:bg-background/50"
            >
              <span className="font-mono text-[11px] text-muted-foreground">
                {new Date(h.created_at).toLocaleDateString([], {
                  month: "short",
                  day: "numeric",
                })}
              </span>
              <span className="min-w-0 flex-1 truncate text-sm">
                {h.question}
              </span>
              {h.flagged && (
                <span
                  className="size-1.5 rounded-full bg-warning"
                  title="flagged"
                />
              )}
              {h.feedback === "up" && (
                <ThumbsUp className="size-3.5 text-success" />
              )}
              {h.feedback === "down" && (
                <ThumbsDown className="size-3.5 text-danger" />
              )}
              <RouteBadge route={h.route} />
              <ChevronRight className="size-4 text-muted-foreground" />
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
