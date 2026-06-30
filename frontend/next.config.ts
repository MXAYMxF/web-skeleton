import type { NextConfig } from "next";

// Single source of truth for the backend URL: configured in .env
// (NEXT_PUBLIC_API_URL), not hardcoded here. The same value is shown in the UI.
const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
