import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// Dedicated HR Agent ports (see frontend/.env) — not 5173/8080 used by other projects.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const frontendPort = Number(env.VITE_DEV_PORT || 5288);
  const apiTarget = env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8808";

  return {
    plugins: [react()],
    server: {
      host: true,
      port: frontendPort,
      strictPort: true, // fail if taken — do not silently jump to 5174/etc.
      proxy: {
        "/positions": apiTarget,
        "/pipeline": apiTarget,
        "/reports": apiTarget,
        "/health": apiTarget,
        "/docs": apiTarget,
        "/openapi.json": apiTarget,
      },
    },
  };
});
