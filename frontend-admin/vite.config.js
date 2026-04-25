import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: "127.0.0.1",
    proxy: {
      "/ip-guard": {
        target: "http://127.0.0.1:8010",
        changeOrigin: true,
      },
      "/admin": {
        target: "http://127.0.0.1:8010",
        changeOrigin: true,
      },
    },
  },
});
