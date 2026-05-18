"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function AdminLoginPage() {
  const router = useRouter();
  const [pw, setPw] = useState("");
  const [error, setError] = useState(false);
  const [pending, setPending] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!pw) return;
    setPending(true);
    setError(false);
    // Mock gate — any non-empty password works; real gate lands with the backend.
    setTimeout(() => {
      if (pw.trim().length >= 1) {
        router.push("/admin");
      } else {
        setError(true);
        setPending(false);
      }
    }, 500);
  };

  return (
    <div className="dark">
      <div className="telemetry-grid relative flex min-h-screen items-center justify-center bg-background px-4 text-foreground">
        <div className="absolute left-0 top-0 h-0.5 w-full bg-primary" />
        <div className="w-full max-w-sm rounded-md border border-border bg-secondary p-7">
          <div className="flex items-center gap-2.5">
            <span className="inline-flex size-7 items-center justify-center rounded-sm bg-primary font-display text-[13px] text-primary-foreground">
              F1
            </span>
            <div>
              <div className="font-display text-sm tracking-[0.06em]">
                OBSERVABILITY
              </div>
              <div className="label-micro">cockpit access</div>
            </div>
          </div>

          <form onSubmit={submit} className="mt-7 space-y-3">
            <label className="label-micro block">admin password</label>
            <input
              type="password"
              value={pw}
              onChange={(e) => setPw(e.target.value)}
              autoFocus
              className="w-full rounded-sm border border-border bg-background/50 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/40"
              placeholder="••••••••"
            />
            {error && (
              <p className="font-mono text-[11px] text-danger">
                Incorrect password.
              </p>
            )}
            <Button type="submit" className="w-full" disabled={pending}>
              {pending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                "Enter"
              )}
            </Button>
          </form>

          <p className="mt-5 text-[11px] leading-relaxed text-muted-foreground">
            Single admin, password-protected. Public users never see this — the
            real gate (signed cookie via the ADMIN_PASSWORD env var) lands with
            the FastAPI backend.
          </p>
          <Link
            href="/"
            className="mt-4 block font-mono text-[11px] text-muted-foreground hover:text-foreground"
          >
            ← back to public app
          </Link>
        </div>
      </div>
    </div>
  );
}
