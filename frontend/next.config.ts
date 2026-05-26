import type { NextConfig } from "next";

const BACKEND = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND}/api/:path*` },
      { source: "/r/:path*", destination: `${BACKEND}/r/:path*` },
      { source: "/healthz", destination: `${BACKEND}/healthz` },
      { source: "/readyz", destination: `${BACKEND}/readyz` },
    ];
  },
};

export default nextConfig;
