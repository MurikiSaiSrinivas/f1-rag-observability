import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  // Pin the workspace root to this folder — a stray lockfile in the user's
  // home directory would otherwise be inferred as the root.
  turbopack: {
    root: path.resolve(import.meta.dirname),
  },
};

export default nextConfig;
