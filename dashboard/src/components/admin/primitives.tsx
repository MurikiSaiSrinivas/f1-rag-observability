import type { CSSProperties, ReactNode } from "react";

import { cn } from "@/lib/utils";

const reveal = (i: number) =>
  ({ ["--i"]: i }) as CSSProperties;

export function PageHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <header className="reveal space-y-1" style={reveal(0)}>
      <h1 className="font-display text-3xl tracking-tight">{title}</h1>
      {subtitle && (
        <p className="text-sm text-muted-foreground">{subtitle}</p>
      )}
    </header>
  );
}

export function Panel({
  title,
  right,
  className,
  children,
  i = 1,
}: {
  title?: string;
  right?: ReactNode;
  className?: string;
  children: ReactNode;
  i?: number;
}) {
  return (
    <div
      className={cn(
        "reveal rounded-md border border-border bg-secondary",
        className,
      )}
      style={reveal(i)}
    >
      {title && (
        <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
          <span className="label-micro">{title}</span>
          {right}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}

export function StatTile({
  label,
  value,
  unit,
  delta,
  deltaTone = "muted",
  i = 0,
}: {
  label: string;
  value: string;
  unit?: string;
  delta?: string;
  deltaTone?: "up" | "down" | "muted";
  i?: number;
}) {
  return (
    <div
      className="reveal rounded-md border border-border bg-secondary p-4"
      style={reveal(i)}
    >
      <div className="label-micro">{label}</div>
      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="readout text-3xl">{value}</span>
        {unit && (
          <span className="font-mono text-[11px] text-muted-foreground">
            {unit}
          </span>
        )}
      </div>
      {delta && (
        <div
          className={cn(
            "mt-2 font-mono text-[11px]",
            deltaTone === "up" && "text-success",
            deltaTone === "down" && "text-danger",
            deltaTone === "muted" && "text-muted-foreground",
          )}
        >
          {delta}
        </div>
      )}
    </div>
  );
}

export function Sparkline({
  data,
  color = "var(--primary)",
  className,
}: {
  data: number[];
  color?: string;
  className?: string;
}) {
  if (data.length < 2) return null;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const span = max - min || 1;
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * 100;
      const y = 100 - ((v - min) / span) * 100;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      className={cn("h-8 w-full", className)}
    >
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth={2}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

export function Bars({
  items,
}: {
  items: { label: string; value: number; sub?: string; color?: string }[];
}) {
  const max = Math.max(...items.map((d) => d.value), 1);
  return (
    <div className="space-y-2.5">
      {items.map((d) => (
        <div key={d.label} className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="font-mono">{d.label}</span>
            <span className="font-mono tabular text-muted-foreground">
              {d.sub ?? d.value.toLocaleString()}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-sm bg-background">
            <div
              className="h-full rounded-sm"
              style={{
                width: `${(d.value / max) * 100}%`,
                background: d.color ?? "var(--primary)",
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function Columns({
  data,
  color = "var(--primary)",
  height = 160,
}: {
  data: { label: string; value: number; sub?: string }[];
  color?: string;
  height?: number;
}) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div>
      <div
        className="flex items-end gap-2"
        style={{ height }}
      >
        {data.map((d) => (
          <div
            key={d.label}
            className="group flex flex-1 flex-col items-center justify-end"
          >
            <span className="mb-1 font-mono text-[10px] text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100">
              {d.sub ?? d.value.toLocaleString()}
            </span>
            <div
              className="w-full rounded-t-sm transition-all"
              style={{
                height: `${Math.max((d.value / max) * 100, 1)}%`,
                background: color,
              }}
            />
          </div>
        ))}
      </div>
      <div className="mt-2 flex gap-2">
        {data.map((d) => (
          <span
            key={d.label}
            className="flex-1 truncate text-center font-mono text-[10px] text-muted-foreground"
          >
            {d.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export function Donut({
  segments,
  total,
  centerLabel,
}: {
  segments: { label: string; value: number; color: string }[];
  total?: number;
  centerLabel?: string;
}) {
  const sum =
    (total ?? segments.reduce((a, s) => a + s.value, 0)) || 1;
  const R = 42;
  const C = 2 * Math.PI * R;
  let offset = 0;
  return (
    <div className="flex items-center gap-6">
      <svg viewBox="0 0 100 100" className="size-32 -rotate-90">
        {segments.map((s) => {
          const len = (s.value / sum) * C;
          const el = (
            <circle
              key={s.label}
              cx="50"
              cy="50"
              r={R}
              fill="none"
              stroke={s.color}
              strokeWidth={12}
              strokeDasharray={`${len} ${C - len}`}
              strokeDashoffset={-offset}
            />
          );
          offset += len;
          return el;
        })}
      </svg>
      <div className="space-y-2">
        {centerLabel && (
          <div className="readout text-2xl">{centerLabel}</div>
        )}
        {segments.map((s) => (
          <div key={s.label} className="flex items-center gap-2 text-xs">
            <span
              className="size-2.5 rounded-[2px]"
              style={{ background: s.color }}
            />
            <span className="font-mono">{s.label}</span>
            <span className="font-mono tabular text-muted-foreground">
              {Math.round((s.value / sum) * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function LineChart({
  series,
  labels,
  height = 200,
}: {
  series: { name: string; points: number[]; color: string }[];
  labels: string[];
  height?: number;
}) {
  const all = series.flatMap((s) => s.points);
  const max = Math.max(...all, 1);
  const min = Math.min(...all, 0);
  const span = max - min || 1;
  const toPts = (pts: number[]) =>
    pts
      .map((v, i) => {
        const x = (i / Math.max(pts.length - 1, 1)) * 100;
        const y = 100 - ((v - min) / span) * 100;
        return `${x},${y}`;
      })
      .join(" ");
  return (
    <div>
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        style={{ height }}
        className="w-full"
      >
        {[25, 50, 75].map((y) => (
          <line
            key={y}
            x1="0"
            x2="100"
            y1={y}
            y2={y}
            stroke="var(--border)"
            strokeWidth={0.5}
            vectorEffect="non-scaling-stroke"
          />
        ))}
        {series.map((s) => (
          <polyline
            key={s.name}
            points={toPts(s.points)}
            fill="none"
            stroke={s.color}
            strokeWidth={2}
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </svg>
      <div className="mt-2 flex justify-between">
        {labels.map((l) => (
          <span
            key={l}
            className="font-mono text-[10px] text-muted-foreground"
          >
            {l}
          </span>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
        {series.map((s) => (
          <span
            key={s.name}
            className="flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground"
          >
            <span
              className="h-0.5 w-3"
              style={{ background: s.color }}
            />
            {s.name}
          </span>
        ))}
      </div>
    </div>
  );
}

/** span_type -> CSS color, for charts that key off span colors */
export const SPAN_COLOR: Record<string, string> = {
  guardrail: "var(--span-guardrail)",
  llm: "var(--span-llm)",
  retrieval: "var(--span-retrieval)",
  sql: "var(--span-sql)",
  orchestration: "var(--span-orchestration)",
};

export const ROUTE_COLOR: Record<string, string> = {
  narrative: "var(--route-narrative)",
  structured: "var(--route-structured)",
  both: "var(--route-both)",
};
