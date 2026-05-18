import Link from "next/link";

/**
 * PUBLIC app shell — light theme, pit-wall telemetry skin.
 * Thin red livery rule on top, Saira wordmark, faint data-screen grid.
 */
export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="telemetry-grid flex min-h-full flex-col bg-background text-foreground">
      {/* livery accent */}
      <div className="h-0.5 w-full bg-primary" />

      <header className="sticky top-0 z-30 border-b border-border bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="inline-flex size-7 items-center justify-center rounded-sm bg-primary font-display text-[13px] text-primary-foreground">
              F1
            </span>
            <span className="font-display text-[16px] tracking-[0.02em]">
              RAG Observability
            </span>
          </Link>
          <nav className="flex items-center gap-7 text-[13px]">
            <Link
              href="/history"
              className="text-muted-foreground transition-colors hover:text-foreground"
            >
              My history
            </Link>
            <Link
              href="/login"
              className="text-muted-foreground/50 transition-colors hover:text-foreground"
            >
              Admin
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10">
        {children}
      </main>

      <footer className="border-t border-border py-4 text-center">
        <span className="label-micro">
          no account · saved to this browser only
        </span>
      </footer>
    </div>
  );
}
