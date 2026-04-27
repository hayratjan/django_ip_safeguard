import { defineStore } from "pinia";
import i18n, { STORAGE_KEY } from "../i18n";
import { i18nLangListApi, i18nLangSwitchApi } from "../api";

const BACKEND_LANG_MAP = { zh: "zh-hans", en: "en" };

function normalizeFrontendLang(lang) {
  if (!lang) return "zh";
  const normalized = lang.toLowerCase().replace(/[_-]/g, "");
  if (normalized === "zh" || normalized === "zhcn" || normalized === "zhhans" || normalized === "zh-hans" || normalized === "zh_hans") {
    return "zh";
  }
  if (normalized === "en" || normalized === "enen" || normalized === "enus") {
    return "en";
  }
  return lang;
}

function toBackendLang(locale) {
  return BACKEND_LANG_MAP[locale] || locale;
}

function isLocaleDifferent(loc1, loc2) {
  return normalizeFrontendLang(loc1) !== normalizeFrontendLang(loc2);
}

export const useI18nStore = defineStore("i18n", {
  state: () => ({
    currentLocale: normalizeFrontendLang(i18n.global.locale.value),
    languages: [
      { code: "zh", name: "简体中文" },
      { code: "en", name: "English" },
    ],
  }),
  actions: {
    setLocale(locale) {
      const normalized = normalizeFrontendLang(locale);
      if (!isLocaleDifferent(normalized, this.currentLocale)) return;
      this.currentLocale = normalized;
      i18n.global.locale.value = normalized;
      localStorage.setItem(STORAGE_KEY, normalized);
      document.documentElement.setAttribute("lang", normalized === "zh" ? "zh-Hans" : "en");
    },
    async switchLocale(locale) {
      this.setLocale(locale);
      try {
        await i18nLangSwitchApi({ language: toBackendLang(locale) });
      } catch {
        // silently ignore backend switch failure
      }
    },
    async fetchLanguages() {
      try {
        const data = await i18nLangListApi();
        if (data?.languages) {
          this.languages = data.languages.map((l) => ({
            code: normalizeFrontendLang(l.code),
            name: l.name,
          }));
        }
        if (data?.current) {
          const fe = normalizeFrontendLang(data.current);
          if (isLocaleDifferent(fe, this.currentLocale)) {
            this.setLocale(fe);
          }
        }
      } catch {
        // silently ignore
      }
    },
  },
});
