"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";

/**
 * App-wide client providers.
 *
 * TanStack Query is the data layer for the whole tree — components call
 * `useQuery` against src/lib/api.ts, which today resolves typed fixtures and
 * later resolves the real FastAPI backend with zero component changes.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 30_000, refetchOnWindowFocus: false },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={150}>
        {children}
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}
