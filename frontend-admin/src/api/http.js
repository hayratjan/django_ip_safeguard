import axios from "axios";
import { ElMessage } from "element-plus";
import router from "../router";
import i18n from "../i18n";

export const JWT_ACCESS_KEY = "ip_guard_access_token";
export const JWT_REFRESH_KEY = "ip_guard_refresh_token";

export function setJwtTokens(accessToken, refreshToken) {
  if (accessToken) {
    localStorage.setItem(JWT_ACCESS_KEY, accessToken);
  }
  if (refreshToken) {
    localStorage.setItem(JWT_REFRESH_KEY, refreshToken);
  }
}

export function clearJwtTokens() {
  localStorage.removeItem(JWT_ACCESS_KEY);
  localStorage.removeItem(JWT_REFRESH_KEY);
}

const rawApi = axios.create({
  baseURL: "/ip-guard/api",
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  timeout: 10000,
});

const http = axios.create({
  baseURL: "/ip-guard/api",
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  timeout: 10000,
});

http.interceptors.request.use((config) => {
  const token = localStorage.getItem(JWT_ACCESS_KEY);
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  const savedLang = localStorage.getItem("ip_guard_locale");
  if (savedLang) {
    config.headers = config.headers || {};
    config.headers["Accept-Language"] = savedLang === "zh" ? "zh-hans" : "en";
  }
  return config;
});

async function tryRefreshAccessToken() {
  const refresh = localStorage.getItem(JWT_REFRESH_KEY);
  if (!refresh) {
    return false;
  }
  try {
    const res = await rawApi.post("/auth/jwt/refresh/", { refresh_token: refresh });
    const body = res.data || {};
    if (body.code !== 0 || !body.data?.access_token) {
      return false;
    }
    localStorage.setItem(JWT_ACCESS_KEY, body.data.access_token);
    return true;
  } catch {
    return false;
  }
}

const t = i18n.global.t.bind(i18n.global);

http.interceptors.response.use(
  (response) => {
    const payload = response.data || {};
    if (payload.code !== 0) {
      ElMessage.error(payload.message || t("common.failed"));
      return Promise.reject(payload);
    }
    return payload.data;
  },
  async (error) => {
    const status = error?.response?.status;
    const original = error.config || {};
    if (status === 401 && !original.__jwtRetried) {
      const ok = await tryRefreshAccessToken();
      if (ok) {
        original.__jwtRetried = true;
        original.headers = original.headers || {};
        const tok = localStorage.getItem(JWT_ACCESS_KEY);
        if (tok) {
          original.headers.Authorization = `Bearer ${tok}`;
        }
        return http(original);
      }
    }
    if (status === 401) {
      clearJwtTokens();
      ElMessage.warning(t("auth.sessionExpired"));
      router.push("/login");
    } else if (status === 403) {
      const msg = error?.response?.data?.message;
      ElMessage.error(msg || t("auth.noPermission"));
    } else {
      ElMessage.error(error?.response?.data?.message || t("auth.networkError"));
    }
    return Promise.reject(error);
  }
);

export default http;
