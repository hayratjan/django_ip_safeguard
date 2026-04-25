import { defineStore } from "pinia";
import { meApi } from "../api";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null,
    loaded: false,
  }),
  actions: {
    async fetchMe() {
      try {
        const data = await meApi();
        this.user = data;
      } catch (_e) {
        this.user = null;
      } finally {
        this.loaded = true;
      }
    },
    clear() {
      this.user = null;
      this.loaded = true;
    },
  },
});
