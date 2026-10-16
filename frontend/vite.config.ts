/// <reference types="vitest/config" />
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
  test: {
    // 기본값은 CSS를 빈 문자열로 바꾼다. 스타일 규칙 테스트(tokens·responsive)가 원문(?raw)을 읽도록 켠다.
    css: true,
  },
});
