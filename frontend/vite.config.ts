import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// All deps are bundled locally at build time — no CDN, no runtime fetch from
// outside AFNET (NFR-3 / AC-21). The dev proxy points the API at the backend.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8011",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
