import { defineConfig } from "vite";
export default defineConfig({
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/docs": "http://127.0.0.1:8000",
      "/openapi.json": "http://127.0.0.1:8000",
      "/redoc": "http://127.0.0.1:8000",
    },
  },
  build: { outDir: "dist" },
});
