import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Research Vault",
    short_name: "Research Vault",
    description: "Self-hosted research and knowledge management platform",
    start_url: "/dashboard",
    display: "standalone",
    background_color: "#f4f3ef",
    theme_color: "#2563eb",
    icons: [
      {
        src: "/icon-192",
        sizes: "192x192",
        type: "image/png",
      },
      {
        src: "/icon-512",
        sizes: "512x512",
        type: "image/png",
      },
    ],
  };
}
