import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { FinalStatus, Route, Severity } from "@/lib/types";

const ROUTE_CLS: Record<Route, string> = {
  narrative: "border-route-narrative/40 text-route-narrative",
  structured: "border-route-structured/40 text-route-structured",
  both: "border-route-both/40 text-route-both",
};

export function RouteBadge({ route }: { route: Route }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "rounded-sm font-mono text-[10px] uppercase tracking-wider",
        ROUTE_CLS[route],
      )}
    >
      {route}
    </Badge>
  );
}

const STATUS_CLS: Record<FinalStatus, string> = {
  success: "bg-success text-success-foreground",
  error: "bg-danger text-danger-foreground",
  refused: "bg-warning text-warning-foreground",
  flagged: "bg-warning text-warning-foreground",
};

export function StatusBadge({ status }: { status: FinalStatus }) {
  return (
    <Badge
      className={cn(
        "rounded-sm font-mono text-[10px] uppercase tracking-wider",
        STATUS_CLS[status],
      )}
    >
      {status}
    </Badge>
  );
}

const SEVERITY_CLS: Record<Severity, string> = {
  info: "border-muted-foreground/40 text-muted-foreground",
  warning: "border-warning/50 text-warning",
  critical: "border-danger/50 text-danger",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "rounded-sm font-mono text-[10px] uppercase tracking-wider",
        SEVERITY_CLS[severity],
      )}
    >
      {severity}
    </Badge>
  );
}
