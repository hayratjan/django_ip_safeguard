import { defineStore } from "pinia";

const THEME_KEY = "ip_guard_theme";
const COLOR_KEY = "ip_guard_color";

const THEME_OPTIONS = [
  { value: "light", label: "亮色" },
  { value: "dark", label: "暗色" },
  { value: "auto", label: "跟随系统" },
];

const COLOR_OPTIONS = [
  { value: "#409eff", label: "默认蓝" },
  { value: "#6366f1", label: "靛蓝" },
  { value: "#8b5cf6", label: "紫色" },
  { value: "#10b981", label: "翡翠绿" },
  { value: "#f59e0b", label: "琥珀" },
  { value: "#ef4444", label: "红色" },
  { value: "#ec4899", label: "粉色" },
  { value: "#06b6d4", label: "青色" },
];

function isValidHex(hex) {
  return /^#[0-9a-fA-F]{6}$/.test(hex);
}

function getSystemTheme() {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme) {
  const actual = theme === "auto" ? getSystemTheme() : theme;
  document.documentElement.setAttribute("data-theme", actual);
  if (actual === "dark") {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
}

function applyColor(color) {
  document.documentElement.style.setProperty("--el-color-primary", color);
  const r = parseInt(color.slice(1, 3), 16);
  const g = parseInt(color.slice(3, 5), 16);
  const b = parseInt(color.slice(5, 7), 16);
  for (let i = 1; i <= 9; i++) {
    const mix = i / 10;
    const mixR = Math.round(r + (255 - r) * mix);
    const mixG = Math.round(g + (255 - g) * mix);
    const mixB = Math.round(b + (255 - b) * mix);
    const hex = `#${mixR.toString(16).padStart(2, "0")}${mixG.toString(16).padStart(2, "0")}${mixB.toString(16).padStart(2, "0")}`;
    document.documentElement.style.setProperty(`--el-color-primary-light-${10 - i}`, hex);
  }
  document.documentElement.style.setProperty("--el-color-primary-dark-2", `rgb(${Math.round(r * 0.8)}, ${Math.round(g * 0.8)}, ${Math.round(b * 0.8)})`);
}

export const useThemeStore = defineStore("theme", {
  state: () => ({
    theme: localStorage.getItem(THEME_KEY) || "light",
    primaryColor: localStorage.getItem(COLOR_KEY) || "#409eff",
    themeOptions: THEME_OPTIONS,
    colorOptions: COLOR_OPTIONS,
  }),
  getters: {
    isDark: (state) => {
      return state.theme === "auto" ? getSystemTheme() === "dark" : state.theme === "dark";
    },
    actualTheme: (state) => {
      return state.theme === "auto" ? getSystemTheme() : state.theme;
    },
  },
  actions: {
    init() {
      applyTheme(this.theme);
      applyColor(this.primaryColor);
      if (this.theme === "auto") {
        window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
          applyTheme(this.theme);
        });
      }
    },
    setTheme(theme) {
      this.theme = theme;
      localStorage.setItem(THEME_KEY, theme);
      applyTheme(theme);
    },
    setPrimaryColor(color) {
      if (!isValidHex(color)) return;
      this.primaryColor = color;
      localStorage.setItem(COLOR_KEY, color);
      applyColor(color);
    },
  },
});
