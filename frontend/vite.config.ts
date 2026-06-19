import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// All deps are bundled locally at build time — no CDN, no runtime fetch from
// outside AFNET (NFR-3 / AC-21). The dev proxy points the API at the backend.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,            // listen on 0.0.0.0 so a remote browser can reach it
    allowedHosts: true,    // accept any Host header (dev demo behind an IP/tunnel)
    proxy: {
      "/api": {
        target: "http://localhost:3003",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
