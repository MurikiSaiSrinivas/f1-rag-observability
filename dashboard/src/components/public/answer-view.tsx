"use client";

import { useState } from "react";
import type { CSSProperties } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  AlertTriangle,
  ArrowLeft,
  ChevronDown,
  ExternalLink,
  RotateCcw,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";

import { api, queryKeys } from "@/lib/api";
import type { AnswerView as AnswerViewT } from "@/lib/types";
import { RouteBadge, StatusBadge } from "@/components/badges";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

const step = (i: number) => ({ ["--i"]: i }) as CSSProperties;

function HighlightedText({
  text,
  highlights,
}: {
  text: string;
  highlights: { start: number; end: number }[];
}) {
  const sorted = [...highlights].sort((a, b) => a.start - b.start);
  const out: React.ReactNode[] = [];
  let cursor = 0;
  sorted.forEach((h, i) => {
    if (h.start > cursor)
      out.push(<span key={`t${i}`}>{text.slice(cursor, h.start)}</span>);
    out.push(
      <mark
        key={`h${i}`}
        className="rounded-sm bg-amber-200 px-0.5 text-zinc-900"
      >
        {text.slice(h.start, h.end)}
      </mark>,
    );
    cursor = h.end;
  });
  if (cursor < text.length)
    out.push(<span key="t-end">{text.slice(cursor)}</span>);
  return <p className="text-sm leading-7">{out}</p>;
}

function SourceReader({ a }: { a: AnswerViewT }) {
  const [showUnused, setShowUnused] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const src = a.source;
  if (!src)
    return (
      <p className="text-sm text-muted-foreground">
        No source document for this answer.
      </p>
    );
  const used = a.retrieved.filter((c) => c.used_in_prompt).length;
  const chunks = showUnused
    ? a.retrieved
    : a.retrieved.filter((c) => c.used_in_prompt);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">{src.title}</div>
          <a
            href={src.url}
            target="_blank"
            rel="noreferrer"
            className="mt-0.5 inline-flex items-center gap-1 font-mono text-[11px] text-muted-foreground hover:text-foreground"
          >
            {src.kind === "fia" && src.page_number != null
              ? `FIA · p.${src.page_number}`
              : "wikipedia"}
            <ExternalLink className="size-3" />
          </a>
        </div>
        <span className="label-micro shrink-0 tracking-wide">
          {a.retrieved.length} retrieved · {used} used
        </span>
      </div>

      <div className="max-h-[360px] overflow-y-auto rounded-md border border-border bg-background/40 p-4">
        <HighlightedText
          text={src.document_text}
          highlights={src.highlights}
        />
      </div>

      <div className="space-y-2">
        <button
          type="button"
          onClick={() => setShowUnused((v) => !v)}
          className="flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground hover:text-foreground"
        >
          <ChevronDown
            className={cn(
              "size-3 transition-transform",
              showUnused && "rotate-180",
            )}
          />
          {showUnused ? "hide" : "show"} retrieved-but-unused chunks
        </button>
        <div className="overflow-hidden rounded-md border border-border">
          {chunks.map((c) => {
            const isOpen = open === c.chunk_id;
            return (
              <div
                key={c.chunk_id}
                className="border-b border-border last:border-0"
              >
                <button
                  type="button"
                  onClick={() => setOpen(isOpen ? null : c.chunk_id)}
                  className={cn(
                    "flex w-full items-center gap-3 px-3 py-1.5 text-left transition-colors hover:bg-background/40",
                    !c.used_in_prompt && !isOpen && "opacity-50",
                  )}
                >
                  <ChevronDown
                    className={cn(
                      "size-3 shrink-0 text-muted-foreground transition-transform",
                      isOpen && "rotate-180",
                    )}
                  />
                  <span className="w-5 text-center font-mono text-[11px] text-muted-foreground">
                    {c.rank}
                  </span>
                  <span
                    className={cn(
                      "w-10 text-right font-mono text-[11px] tabular",
                      c.similarity >= 0.5 ? "text-success" : "text-warning",
                    )}
                  >
                    {c.similarity.toFixed(2)}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-xs">
                    {c.title}
                  </span>
                  <span className="label-micro tracking-wide">{c.source}</span>
                  <span
                    className={cn(
                      "rounded-sm px-1.5 py-0.5 font-mono text-[10px] uppercase",
                      c.used_in_prompt
                        ? "bg-success/15 text-success"
                        : "bg-muted text-muted-foreground",
                    )}
                  >
                    {c.used_in_prompt ? "used" : "trimmed"}
                  </span>
                </button>
                {isOpen && (
                  <div className="space-y-2 border-t border-border bg-background/40 px-3 py-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="label-micro truncate">
                        {c.chunk_id}
                      </span>
                      {c.used_in_prompt ? (
                        <span className="shrink-0 font-mono text-[10px] text-success">
                          ▲ highlighted above
                        </span>
                      ) : (
                        <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
                          retrieved · not sent to the model
                        </span>
                      )}
                    </div>
                    <p className="text-sm leading-6">{c.text}</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function SqlPanel({ a }: { a: AnswerViewT }) {
  const sql = a.sql;
  if (!sql)
    return (
      <p className="text-sm text-muted-foreground">
        No database query for this answer.
      </p>
    );
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <span className="label-micro">generated query</span>
        <span className="font-mono text-[11px] text-muted-foreground">
          {sql.row_count} rows
        </span>
      </div>
      <pre className="overflow-x-auto rounded-md border border-border bg-background/40 p-3 font-mono text-[11px] leading-relaxed">
        {sql.query}
      </pre>
      {sql.rows.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                {Object.keys(sql.rows[0]).map((k) => (
                  <th key={k} className="label-micro px-3 py-2 text-left">
                    {k}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sql.rows.map((row, i) => (
                <tr key={i} className="border-b border-border last:border-0">
                  {Object.values(row).map((v, j) => (
                    <td
                      key={j}
                      className="px-3 py-2 font-mono text-xs tabular"
                    >
                      {String(v)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-muted-foreground">
        Computed directly from the F1 results database — not retrieved text.
      </p>
    </div>
  );
}

function Provenance({ a }: { a: AnswerViewT }) {
  if (a.route === "structured") return <SqlPanel a={a} />;
  if (a.route === "narrative") return <SourceReader a={a} />;
  return (
    <Tabs defaultValue="database" className="gap-0">
      <TabsList className="bg-transparent p-0">
        <TabsTrigger
          value="database"
          className="rounded-none border-b-2 border-transparent px-3 py-2 data-[state=active]:border-primary"
        >
          Database
        </TabsTrigger>
        <TabsTrigger
          value="sources"
          className="rounded-none border-b-2 border-transparent px-3 py-2 data-[state=active]:border-primary"
        >
          Sources
        </TabsTrigger>
      </TabsList>
      <TabsContent value="database" className="pt-4">
        <SqlPanel a={a} />
      </TabsContent>
      <TabsContent value="sources" className="pt-4">
        <SourceReader a={a} />
      </TabsContent>
    </Tabs>
  );
}

function GuardrailBanner({ a }: { a: AnswerViewT }) {
  const [open, setOpen] = useState(false);
  if (a.guardrails.length === 0) return null;
  return (
    <div className="rounded-md border border-warning/40 bg-warning/10 p-3">
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" />
        <div className="min-w-0 flex-1">
          <p className="text-sm">
            This answer was flagged —{" "}
            <span className="text-muted-foreground">
              {a.guardrails.map((g) => g.rule_name).join(", ")}. Treat it with
              caution.
            </span>
          </p>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="mt-1 font-mono text-[11px] text-warning hover:underline"
          >
            {open ? "hide" : "why?"}
          </button>
          {open && (
            <ul className="mt-2 space-y-2">
              {a.guardrails.map((g) => (
                <li key={g.id} className="text-xs text-muted-foreground">
                  <span className="font-mono text-foreground">
                    {g.rule_name}
                  </span>{" "}
                  ({g.stage} · {g.severity}) — {g.reason}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <div className="space-y-4 lg:col-span-3">
        <Skeleton className="h-6 w-40 rounded-sm" />
        <Skeleton className="h-32 w-full rounded-md" />
      </div>
      <Skeleton className="h-80 w-full rounded-md lg:col-span-2" />
    </div>
  );
}

export function AnswerView({ requestId }: { requestId: string }) {
  const { data: a, isLoading, isError } = useQuery({
    queryKey: queryKeys.answer(requestId),
    queryFn: () => api.getAnswer(requestId),
  });
  const [vote, setVote] = useState<"up" | "down" | null>(null);

  if (isLoading) return <LoadingState />;
  if (isError || !a)
    return (
      <div className="rounded-md border border-border bg-secondary p-5 text-sm text-danger">
        Could not load this answer.
      </div>
    );

  const currentVote = vote ?? a.feedback;

  return (
    <div className="space-y-6">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" /> Ask another question
      </Link>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* answer */}
        <div className="reveal space-y-5 lg:col-span-3" style={step(0)}>
          <div className="flex items-center gap-2">
            <RouteBadge route={a.route} />
            {a.status === "flagged" && <StatusBadge status={a.status} />}
          </div>

          <h1 className="font-display text-2xl leading-snug tracking-tight">
            {a.question}
          </h1>

          <GuardrailBanner a={a} />

          <p className="text-[15px] leading-7">{a.answer}</p>

          <div className="space-y-3 border-t border-border pt-4">
            <div className="flex items-center gap-2">
              <span className="label-micro">was this helpful</span>
              <Button
                variant="ghost"
                size="sm"
                className={cn(currentVote === "up" && "text-success")}
                onClick={() => {
                  setVote("up");
                  toast("Thanks for the feedback.");
                }}
              >
                <ThumbsUp className="size-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className={cn(currentVote === "down" && "text-danger")}
                onClick={() => {
                  setVote("down");
                  toast("Thanks — logged for review.");
                }}
              >
                <ThumbsDown className="size-4" />
              </Button>
            </div>
            <textarea
              placeholder="Add a comment (optional)…"
              className="h-20 w-full resize-none rounded-md border border-border bg-secondary p-3 text-sm outline-none focus:ring-2 focus:ring-primary/40"
            />
            <Link
              href={`/replay/${a.request_id}`}
              className="inline-flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground hover:text-foreground"
            >
              <RotateCcw className="size-3" /> replay this question
            </Link>
          </div>
        </div>

        {/* provenance */}
        <div
          className="reveal lg:col-span-2"
          style={step(1)}
        >
          <div className="rounded-md border border-border bg-secondary">
            <div className="border-b border-border px-4 py-2.5">
              <span className="label-micro">where this answer came from</span>
            </div>
            <div className="p-4">
              <Provenance a={a} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
