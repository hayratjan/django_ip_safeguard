import { createI18n } from "vue-i18n";
import zh from "./zh";
import en from "./en";

const STORAGE_KEY = "ip_guard_locale";

function detectLocale() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && (stored === "zh" || stored === "en")) {
    return stored;
  }
  const navLang = navigator.language || navigator.userLanguage || "";
  if (navLang.toLowerCase().startsWith("zh")) {
    return "zh";
  }
  return "en";
}

const i18n = createI18n({
  legacy: false,
  locale: detectLocale(),
  fallbackLocale: "zh",
  messages: { zh, en },
});

export default i18n;
export { STORAGE_KEY };
