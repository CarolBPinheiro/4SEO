import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Export estático para publicar marketing+checkout no mesmo domínio do app (Netlify).
  output: "export",
  images: {
    unoptimized: true,
  },
  trailingSlash: true,
};

export default nextConfig;
