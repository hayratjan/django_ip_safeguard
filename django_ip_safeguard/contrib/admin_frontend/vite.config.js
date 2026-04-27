import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";
import path from "node:path";

const rootDir = path.resolve(__dirname);
const staticFilesDir = path.resolve(rootDir, "static", "admin_frontend");

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  base: "/ip-guard/admin-frontend/",
  build: {
    outDir: staticFilesDir,
    emptyOutDir: true,
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
