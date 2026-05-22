import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The SPA is served by FastAPI under /app, built into ../static/app.
export default defineConfig({
  base: "/app/",
  plugins: [react()],
  build: {
    outDir: "../static/app",
    emptyOutDir: true,
  },
  server: {
    // `npm run dev` proxies the API to the FastAPI server.
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
