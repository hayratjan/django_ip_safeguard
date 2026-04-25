import axios from "axios";
import { ElMessage } from "element-plus";
import router from "../router";

/** 浏览器本地存储的 JWT 键名 */
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

/** 不走业务拦截器，仅用于刷新 token，避免循环依赖 */
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

http.interceptors.response.use(
  (response) => {
    const payload = response.data || {};
    if (payload.code !== 0) {
      ElMessage.error(payload.message || "请求失败");
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
        const t = localStorage.getItem(JWT_ACCESS_KEY);
        if (t) {
          original.headers.Authorization = `Bearer ${t}`;
        }
        return http(original);
      }
    }
    if (status === 401) {
      clearJwtTokens();
      ElMessage.warning("登录状态失效，请重新登录");
      router.push("/login");
    } else if (status === 403) {
      const msg = error?.response?.data?.message;
      ElMessage.error(msg || "没有权限访问该资源");
    } else {
      ElMessage.error(error?.response?.data?.message || "网络异常");
    }
    return Promise.reject(error);
  }
);

export default http;
