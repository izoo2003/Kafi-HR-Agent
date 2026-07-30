import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const frontendPort = Number(env.VITE_DEV_PORT || 5288);
  const apiTarget = env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8808";

  return {
    plugins: [react()],
    server: {
      host: true,
      port: frontendPort,
      strictPort: true,
      proxy: {
        "/api": apiTarget,
        "/health": apiTarget,
        "/docs": apiTarget,
        "/openapi.json": apiTarget,
      },
    },
  };
});
