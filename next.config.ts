import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  images: {
    domains: [], // Add any external image domains you're using here
  },
  // Disable source maps in production for better performance
  productionBrowserSourceMaps: false,
};

export default nextConfig;
