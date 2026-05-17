import type { Metadata } from "next";
import localFont from "next/font/local";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";

// Display — Formula1 Display (self-hosted .woff2, single Regular weight).
// Wordmark, big stat readouts, section labels. Used at its natural weight —
// the F1 timing-screen look is wide + regular, never faux-bold.
const formula1 = localFont({
  src: "./fonts/Formula1-Display.woff2",
  variable: "--font-display",
  weight: "400",
  display: "swap",
  fallback: ["ui-sans-serif", "system-ui", "sans-serif"],
});

// Body / data — IBM Plex Sans. Dense tables stay legible.
const plexSans = IBM_Plex_Sans({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

// Numerics / IDs / SQL — IBM Plex Mono.
const plexMono = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "F1 RAG Observability",
  description:
    "Ask F1 questions with full provenance — and the observability cockpit behind every answer.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${formula1.variable} ${plexSans.variable} ${plexMono.variable} h-full`}
      suppressHydrationWarning
    >
      <body className="min-h-full">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
