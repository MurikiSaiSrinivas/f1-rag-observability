"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  DollarSign,
  Flag,
  Gauge,
  LayoutDashboard,
  ListTree,
  Repeat,
  ShieldAlert,
  Timer,
  Users,
} from "lucide-react";

import { cn } from "@/lib/utils";

const NAV = [
  { label: "Overview", href: "/admin", icon: LayoutDashboard },
  { label: "Traces", href: "/admin/traces", icon: ListTree },
  { label: "Latency", href: "/admin/latency", icon: Timer },
  { label: "Cost", href: "/admin/cost", icon: DollarSign },
  { label: "Quality", href: "/admin/quality", icon: Gauge },
  { label: "Flags / Bad Answers", href: "/admin/flags", icon: Flag },
  { label: "Guardrails", href: "/admin/guardrails", icon: ShieldAlert },
  { label: "Users", href: "/admin/users", icon: Users },
  { label: "Feedback loop", href: "/admin/feedback-loop", icon: Repeat },
];

export function AdminNav() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-0.5 p-3">
      {NAV.map(({ label, href, icon: Icon }) => {
        const active =
          href === "/admin" ? pathname === "/admin" : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
              active
                ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
            )}
          >
            <Icon className="size-4 shrink-0" />
            <span className="truncate">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
