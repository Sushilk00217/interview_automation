
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",

  // Recommended for Static Hosting (avoids next/image optimizer needing a server)
  images: {
    unoptimized: true,
  },
};  

export default nextConfig;


