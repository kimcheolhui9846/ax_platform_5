import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://localhost:8000" },
  },
  build: {
    // 상대 경로는 vite root(frontend/) 기준으로 풀린다. node:path를 쓰지 않아 @types/node가 필요 없다.
    rollupOptions: {
      input: { main: "index.html", preview: "preview.html" },
    },
  },
});
