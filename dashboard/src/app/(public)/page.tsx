"use client";

import { useState } from "react";
import type { CSSProperties } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, Loader2, Search } from "lucide-react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

const step = (i: number) => ({ ["--i"]: i }) as CSSProperties;

const EXAMPLES = [
  { q: "Who is Lando Norris?", tag: "narrative" },
  { q: "How many wins did Verstappen have in 2023?", tag: "data" },
  {
    q: "What happened at the 2021 Abu Dhabi GP and how did the title end?",
    tag: "both",
  },
];

export default function AskHome() {
  const router = useRouter();
  const [question, setQuestion] = useState("");

  const ask = useMutation({
    mutationFn: (q: string) => api.ask(q),
    onSuccess: (res) => router.push(`/answer/${res.request_id}`),
  });

  const submit = (q: string) => {
    const trimmed = q.trim();
    if (!trimmed || ask.isPending) return;
    ask.mutate(trimmed);
  };

  return (
    <div className="mx-auto flex min-h-[68vh] max-w-2xl flex-col items-center justify-center text-center">
      <div className="reveal label-micro" style={step(0)}>
        F1 · seasons 2020–2025
      </div>

      <h1
        className="reveal mt-4 font-display text-5xl leading-[1.05] tracking-tight"
        style={step(1)}
      >
        Ask anything about
        <br />
        Formula 1
      </h1>

      <p className="reveal mt-4 text-sm text-muted-foreground" style={step(2)}>
        Every answer shows exactly where it came from — the source text or the
        database query behind it.
      </p>

      <form
        className="reveal mt-8 w-full"
        style={step(3)}
        onSubmit={(e) => {
          e.preventDefault();
          submit(question);
        }}
      >
        <div className="flex items-center gap-2 rounded-md border border-border bg-secondary p-2 focus-within:ring-2 focus-within:ring-primary/40">
          <Search className="ml-2 size-4 shrink-0 text-muted-foreground" />
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. Who won the 2023 Bahrain Grand Prix?"
            className="min-w-0 flex-1 bg-transparent py-2 text-sm outline-none placeholder:text-muted-foreground"
            autoFocus
          />
          <Button type="submit" disabled={ask.isPending || !question.trim()}>
            {ask.isPending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <>
                Ask <ArrowRight className="size-4" />
              </>
            )}
          </Button>
        </div>
      </form>

      <div
        className="reveal mt-6 flex flex-wrap justify-center gap-2"
        style={step(4)}
      >
        {EXAMPLES.map((ex) => (
          <button
            key={ex.q}
            type="button"
            onClick={() => {
              setQuestion(ex.q);
              submit(ex.q);
            }}
            disabled={ask.isPending}
            className="group flex items-center gap-2 rounded-md border border-border bg-secondary px-3 py-2 text-left text-xs transition-colors hover:border-primary/40 disabled:opacity-50"
          >
            <span className="label-micro tracking-wide text-primary">
              {ex.tag}
            </span>
            <span className="text-muted-foreground group-hover:text-foreground">
              {ex.q}
            </span>
          </button>
        ))}
      </div>

      <p
        className="reveal mt-8 text-xs text-muted-foreground/70"
        style={step(5)}
      >
        No account needed — your questions are saved to this browser only.
      </p>
    </div>
  );
}
