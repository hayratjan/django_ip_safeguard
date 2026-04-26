import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/ip-guard": {
        target: "http://127.0.0.1:8010",
        changeOrigin: true,
        cookieDomainRewrite: { "*": "" },
      },
      "/admin": {
        target: "http://127.0.0.1:8010",
        changeOrigin: true,
        cookieDomainRewrite: { "*": "" },
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["vue", "vue-router", "pinia"],
          element: ["element-plus"],
          echarts: ["echarts", "vue-echarts"],
        },
      },
    },
  },
});
