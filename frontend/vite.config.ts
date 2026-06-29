import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 5173,
    host: true, // bind 0.0.0.0 so Codespaces / containers can forward the port
    allowedHosts: true, // accept the *.app.github.dev forwarded host (dev only)
    proxy: {
      // Proxy API calls to the FastAPI backend during local development.
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
