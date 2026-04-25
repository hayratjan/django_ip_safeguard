import { defineStore } from "pinia";
import i18n, { STORAGE_KEY } from "../i18n";
import { i18nLangListApi, i18nLangSwitchApi } from "../api";

export const useI18nStore = defineStore("i18n", {
  state: () => ({
    currentLocale: i18n.global.locale.value,
    languages: [
      { code: "zh", name: "简体中文" },
      { code: "en", name: "English" },
    ],
  }),
  actions: {
    setLocale(locale) {
      if (locale === this.currentLocale) return;
      this.currentLocale = locale;
      i18n.global.locale.value = locale;
      localStorage.setItem(STORAGE_KEY, locale);
      document.documentElement.setAttribute("lang", locale === "zh" ? "zh-Hans" : "en");
    },
    async switchLocale(locale) {
      this.setLocale(locale);
      try {
        const backendLang = locale === "zh" ? "zh-hans" : "en";
        await i18nLangSwitchApi({ language: backendLang });
      } catch {
        // silently ignore backend switch failure
      }
    },
    async fetchLanguages() {
      try {
        const data = await i18nLangListApi();
        if (data?.languages) {
          this.languages = data.languages.map((l) => ({
            code: l.code === "zh-hans" ? "zh" : l.code,
            name: l.name,
          }));
        }
        if (data?.current) {
          const fe = data.current === "zh-hans" ? "zh" : data.current;
          if (fe !== this.currentLocale) {
            this.setLocale(fe);
          }
        }
      } catch {
        // silently ignore
      }
    },
  },
});
