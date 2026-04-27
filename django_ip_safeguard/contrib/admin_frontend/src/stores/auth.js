import { defineStore } from "pinia";
import { meApi } from "../api";
import { useI18nStore } from "./i18n";

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
        if (data.language) {
          const i18nStore = useI18nStore();
          i18nStore.switchLocale(data.language);
        }
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
    hasPerm(permission) {
      if (!this.user) return false;
      const perms = this.user.permissions || [];
      return perms.includes(permission);
    },
  },
});
