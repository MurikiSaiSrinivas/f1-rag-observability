import Link from "next/link";

import { AdminNav } from "@/components/admin/admin-nav";

/**
 * ADMIN observability cockpit shell — dark, pit-wall telemetry skin.
 * `.dark` flips the subtree to the cockpit palette. Hairline data-screen
 * grid behind the content; instrument micro-labels; crisp geometry.
 */
export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="dark">
      <div className="telemetry-grid flex min-h-full bg-background text-foreground">
        <aside className="sticky top-0 flex h-screen w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
          <div className="h-0.5 w-full bg-primary" />
          <div className="flex h-[55px] items-center gap-2.5 border-b border-sidebar-border px-5">
            <span className="inline-flex size-7 items-center justify-center rounded-sm bg-primary font-display text-[13px] text-primary-foreground">
              F1
            </span>
            <span className="font-display text-[15px] tracking-[0.06em]">
              OBSERVABILITY
            </span>
          </div>
          <div className="flex-1 overflow-y-auto">
            <AdminNav />
          </div>
          <div className="border-t border-sidebar-border p-3">
            <Link
              href="/"
              className="block px-3 py-2 text-xs text-sidebar-foreground/55 transition-colors hover:text-sidebar-foreground"
            >
              ← back to public app
            </Link>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 flex h-[55px] items-center justify-between border-b border-border bg-background/85 px-6 backdrop-blur">
            <span className="label-micro">observability cockpit</span>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-0.5 rounded-md border border-border bg-card p-0.5">
                {["Today", "7d", "30d"].map((r, i) => (
                  <span
                    key={r}
                    className={
                      i === 1
                        ? "rounded-sm bg-secondary px-2.5 py-1 font-mono text-[11px] text-foreground"
                        : "px-2.5 py-1 font-mono text-[11px] text-muted-foreground"
                    }
                  >
                    {r}
                  </span>
                ))}
              </div>
              <span className="flex items-center gap-1.5">
                <span className="relative flex size-2">
                  <span className="absolute inline-flex size-full animate-ping rounded-full bg-success/60" />
                  <span className="relative inline-flex size-2 rounded-full bg-success" />
                </span>
                <span className="label-micro text-success">live</span>
              </span>
            </div>
          </header>

          <main className="flex-1 px-6 py-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
