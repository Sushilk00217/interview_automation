
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
<<<<<<< HEAD
  /* config options here */
  reactStrictMode: false,
=======
  output: "export",

  // Recommended for Static Hosting (avoids next/image optimizer needing a server)
  images: {
    unoptimized: true,
  },
>>>>>>> e625e53 (changes commited)
};

export default nextConfig;
