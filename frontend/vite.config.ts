/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import type { Connect, Plugin } from "vite";

/** 버셀의 /preview → /preview.html(vercel.json rewrites)을 로컬 개발·미리보기 서버에서도 똑같이 한다. */
function previewPath(): Plugin {
  // @types/node가 없어 IncomingMessage에 url 타입이 없다. 필요한 필드만 좁혀 쓴다.
  const rewrite: Connect.NextHandleFunction = (req, _res, next) => {
    const request = req as { url?: string };
    if (request.url === "/preview" || request.url?.startsWith("/preview?")) request.url = request.url.replace("/preview", "/preview.html");
    next();
  };
  return {
    name: "preview-path",
    configureServer: (server) => void server.middlewares.use(rewrite),
    configurePreviewServer: (server) => void server.middlewares.use(rewrite),
  };
}

export default defineConfig({
  plugins: [react(), previewPath()],
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
