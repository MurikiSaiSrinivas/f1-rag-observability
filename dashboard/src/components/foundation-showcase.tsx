import type { CSSProperties } from "react";
import {
  Activity,
  ArrowRight,
  Database,
  Gauge,
  Search,
  ShieldAlert,
  ThumbsUp,
  Timer,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/** stagger helper — feeds the .reveal animation its index */
const step = (i: number) => ({ ["--i"]: i }) as CSSProperties;

const READOUTS = [
  { label: "Latency p95", value: "1980", unit: "ms", icon: Timer },
  { label: "Cost today", value: "0.42", unit: "usd", icon: Database },
  { label: "Faithfulness", value: "0.86", unit: "avg", icon: Gauge },
  { label: "Requests", value: "1287", unit: "24h", icon: Activity },
];

const COLOR_TOKENS = [
  { name: "background", cls: "bg-background border border-border" },
  { name: "card", cls: "bg-card border border-border" },
  { name: "muted", cls: "bg-muted" },
  { name: "secondary", cls: "bg-secondary" },
  { name: "primary", cls: "bg-primary" },
  { name: "border", cls: "bg-border" },
];

const STATUS_TOKENS = [
  { name: "success", cls: "bg-success" },
  { name: "warning", cls: "bg-warning" },
  { name: "danger / error", cls: "bg-danger" },
];

const SPAN_TYPES = [
  { name: "guardrail", cls: "bg-span-guardrail", w: "w-[14%]" },
  { name: "router", cls: "bg-span-orchestration", w: "w-[8%]" },
  { name: "embed", cls: "bg-span-retrieval", w: "w-[10%]" },
  { name: "vector search", cls: "bg-span-retrieval", w: "w-[16%]" },
  { name: "sql exec", cls: "bg-span-sql", w: "w-[12%]" },
  { name: "synthesis", cls: "bg-span-llm", w: "w-[28%]" },
  { name: "output guard", cls: "bg-span-guardrail", w: "w-[7%]" },
];

const SAMPLE_ROWS = [
  {
    id: "req_8f3a2c",
    q: "Who is Lando Norris?",
    route: "narrative" as const,
    lat: "1,240 ms",
    cost: "$0.0008",
    faith: "0.92",
  },
  {
    id: "req_b1d09e",
    q: "How many wins did Verstappen have in 2023?",
    route: "structured" as const,
    lat: "860 ms",
    cost: "$0.0004",
    faith: "—",
  },
  {
    id: "req_4c77a1",
    q: "What happened at the 2021 Abu Dhabi GP and how did the title end?",
    route: "both" as const,
    lat: "3,910 ms",
    cost: "$0.0021",
    faith: "0.78",
  },
];

function RouteBadge({ route }: { route: "narrative" | "structured" | "both" }) {
  const map = {
    narrative: "border-route-narrative/40 text-route-narrative",
    structured: "border-route-structured/40 text-route-structured",
    both: "border-route-both/40 text-route-both",
  };
  return (
    <Badge
      variant="outline"
      className={`${map[route]} rounded-sm font-mono text-[10px] uppercase tracking-wider`}
    >
      {route}
    </Badge>
  );
}

function Swatch({ name, cls }: { name: string; cls: string }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className={`h-12 rounded-sm ${cls}`} />
      <span className="label-micro text-[10px] tracking-wide">{name}</span>
    </div>
  );
}

function SectionTitle({
  index,
  children,
  hint,
}: {
  index: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="mb-5">
      <div className="flex items-center gap-3">
        <span className="font-mono text-[11px] text-primary">{index}</span>
        <h2 className="font-display text-sm uppercase tracking-[0.18em]">
          {children}
        </h2>
        <span className="h-px flex-1 bg-border" />
      </div>
      {hint ? (
        <p className="mt-2 max-w-2xl text-[13px] text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

/**
 * Shared design-system showcase, "pit-wall telemetry" skin. Rendered on the
 * public (light) and admin (dark) preview pages so the visual language can be
 * judged + compared. Foundation only — not a real product screen.
 */
export function FoundationShowcase({ surface }: { surface: string }) {
  return (
    <div className="space-y-14">
      <header className="reveal space-y-4" style={step(0)}>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-sm border border-border bg-card px-2 py-1">
            <span className="size-1.5 rounded-full bg-primary" />
            <span className="label-micro">foundation preview</span>
          </span>
          <span className="label-micro tracking-wide">{surface}</span>
        </div>
        <h1 className="font-display text-[2.75rem] leading-[1.05] tracking-tight">
          Design system &amp; component primitives
        </h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Scaffold, instrumentation typography, theme tokens, layout shells, and
          the component library are wired. No product screens yet — judge the
          look-and-feel here, then we pick screen order together.
        </p>
      </header>

      {/* instrument cluster */}
      <section
        className="reveal grid grid-cols-2 gap-px overflow-hidden rounded-md border border-border bg-border lg:grid-cols-4"
        style={step(1)}
      >
        {READOUTS.map(({ label, value, unit, icon: Icon }) => (
          <div key={label} className="bg-secondary p-5">
            <div className="flex items-center justify-between">
              <span className="label-micro">{label}</span>
              <Icon className="size-3.5 text-muted-foreground" />
            </div>
            <div className="mt-3 flex items-baseline gap-1.5">
              <span className="readout text-4xl">{value}</span>
              <span className="font-mono text-[11px] text-muted-foreground">
                {unit}
              </span>
            </div>
          </div>
        ))}
      </section>

      <section className="reveal" style={step(2)}>
        <SectionTitle
          index="01"
          hint="Racing red = brand/primary. Cool crimson = error/destructive (distinct hue, fixed). Light = public app, dark = admin cockpit."
        >
          Color tokens
        </SectionTitle>
        <div className="grid grid-cols-3 gap-4 sm:grid-cols-6">
          {COLOR_TOKENS.map((t) => (
            <Swatch key={t.name} {...t} />
          ))}
        </div>
        <Separator className="my-6" />
        <div className="grid grid-cols-3 gap-4 sm:grid-cols-6">
          {STATUS_TOKENS.map((t) => (
            <Swatch key={t.name} {...t} />
          ))}
        </div>
      </section>

      <section className="reveal" style={step(3)}>
        <SectionTitle
          index="02"
          hint="The signature trace waterfall colors each span by type. Color legend only — not the real Trace Detail screen."
        >
          Trace-waterfall span palette
        </SectionTitle>
        <div className="space-y-3 rounded-md border border-border bg-secondary p-4">
          <div className="flex h-8 w-full overflow-hidden rounded-sm">
            {SPAN_TYPES.map((s, i) => (
              <div
                key={i}
                className={`${s.cls} ${s.w} border-r border-background/40`}
                title={s.name}
              />
            ))}
          </div>
          <div className="flex flex-wrap gap-x-5 gap-y-1.5">
            {[
              { dot: "bg-span-guardrail", name: "guardrail" },
              { dot: "bg-span-llm", name: "llm" },
              { dot: "bg-span-retrieval", name: "retrieval" },
              { dot: "bg-span-sql", name: "sql" },
              { dot: "bg-span-orchestration", name: "orchestration" },
            ].map(({ dot, name }) => (
              <span
                key={name}
                className="label-micro flex items-center gap-1.5 tracking-wide"
              >
                <span className={`size-2.5 rounded-[2px] ${dot}`} />
                {name}
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="reveal" style={step(4)}>
        <SectionTitle
          index="03"
          hint="Saira for display, IBM Plex Sans for data, IBM Plex Mono for IDs / SQL / latency."
        >
          Typography
        </SectionTitle>
        <div className="space-y-4">
          <p className="font-display text-3xl tracking-tight">
            Saira — pit-wall display type, 1980 ms
          </p>
          <p className="text-sm text-muted-foreground">
            IBM Plex Sans for body and dense table data — engineering character,
            stays legible at small sizes in the cockpit.
          </p>
          <pre className="overflow-x-auto rounded-md border border-border bg-muted/40 p-3.5 font-mono text-xs leading-relaxed">
            {`request_id = req_4c77a1   route = both   latency = 3,910 ms
SELECT driver, COUNT(*) AS wins FROM race_results
WHERE season = 2023 AND position = 1 GROUP BY driver;`}
          </pre>
        </div>
      </section>

      <section className="reveal" style={step(5)}>
        <SectionTitle index="04">Buttons &amp; badges</SectionTitle>
        <div className="flex flex-wrap items-center gap-3">
          <Button>
            <Search className="size-4" /> Ask
          </Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive">Destructive</Button>
          <Button variant="link">
            Replay <ArrowRight className="size-4" />
          </Button>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Badge className="rounded-sm">Default</Badge>
          <Badge variant="secondary" className="rounded-sm">
            Secondary
          </Badge>
          <RouteBadge route="narrative" />
          <RouteBadge route="structured" />
          <RouteBadge route="both" />
          <Badge className="rounded-sm bg-success text-success-foreground">
            success
          </Badge>
          <Badge className="rounded-sm bg-warning text-warning-foreground">
            flagged
          </Badge>
          <Badge className="rounded-sm bg-danger text-danger-foreground">
            error
          </Badge>
        </div>
      </section>

      <section
        className="reveal grid gap-6 lg:grid-cols-2"
        style={step(6)}
      >
        <Card className="rounded-md">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="label-micro">avg latency</span>
              <Gauge className="size-3.5 text-primary" />
            </div>
            <div className="mt-3 readout text-3xl">1,240 ms</div>
            <p className="mt-2 font-mono text-[11px] text-success">
              ▲ 6% vs previous period
            </p>
          </CardContent>
        </Card>

        <Card className="rounded-md">
          <CardContent className="pt-6">
            <span className="label-micro">trace detail panels</span>
            <div className="mt-3">
              <Tabs defaultValue="provenance">
                <TabsList>
                  <TabsTrigger value="provenance">Provenance</TabsTrigger>
                  <TabsTrigger value="scores">Scores</TabsTrigger>
                  <TabsTrigger value="guardrails">Guardrails</TabsTrigger>
                </TabsList>
                <TabsContent
                  value="provenance"
                  className="pt-3 text-sm text-muted-foreground"
                >
                  Retrieved vs. used-in-prompt chunks render here.
                </TabsContent>
                <TabsContent
                  value="scores"
                  className="pt-3 text-sm text-muted-foreground"
                >
                  RAGAS faithfulness / relevance gauges.
                </TabsContent>
                <TabsContent
                  value="guardrails"
                  className="pt-3 text-sm text-muted-foreground"
                >
                  Every guardrail evaluated, with full reasons.
                </TabsContent>
              </Tabs>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="reveal" style={step(7)}>
        <SectionTitle index="05" hint="The shape the real Traces Explorer table will use.">
          Data table
        </SectionTitle>
        <div className="overflow-hidden rounded-md border border-border bg-secondary">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-[120px] label-micro">
                  request_id
                </TableHead>
                <TableHead className="label-micro">question</TableHead>
                <TableHead className="label-micro">route</TableHead>
                <TableHead className="label-micro text-right">latency</TableHead>
                <TableHead className="label-micro text-right">cost</TableHead>
                <TableHead className="label-micro text-right">faith</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {SAMPLE_ROWS.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {r.id}
                  </TableCell>
                  <TableCell className="max-w-[280px] truncate text-sm">
                    {r.q}
                  </TableCell>
                  <TableCell>
                    <RouteBadge route={r.route} />
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs tabular">
                    {r.lat}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs tabular">
                    {r.cost}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs tabular">
                    {r.faith}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </section>

      <section className="reveal" style={step(8)}>
        <SectionTitle index="06">Loading &amp; interaction states</SectionTitle>
        <div className="flex flex-wrap items-center gap-6">
          <div className="space-y-2">
            <Skeleton className="h-4 w-48 rounded-sm" />
            <Skeleton className="h-4 w-32 rounded-sm" />
            <Skeleton className="h-24 w-72 rounded-sm" />
          </div>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="outline">
                <ShieldAlert className="size-4" /> Hover: guardrail
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              Tooltips power span-attribute popovers in the waterfall.
            </TooltipContent>
          </Tooltip>
          <Button variant="ghost" className="text-success">
            <ThumbsUp className="size-4" /> Feedback control
          </Button>
        </div>
      </section>
    </div>
  );
}
