import http, { clearJwtTokens, setJwtTokens } from "./http";

export { clearJwtTokens, setJwtTokens };

export const getCsrf = () => http.get("/auth/csrf/");
export const loginApi = (payload) => http.post("/auth/login/", payload);
export const jwtLoginApi = (payload) => http.post("/auth/jwt/login/", payload);
export const jwtRefreshApi = (payload) => http.post("/auth/jwt/refresh/", payload);
export const jwtLogoutApi = () => http.post("/auth/jwt/logout/");
export const logoutApi = () => http.post("/auth/logout/");
export const meApi = () => http.get("/auth/me/");

export const dashboardApi = () => http.get("/dashboard/");
export const recentRecordsApi = (params) => http.get("/recent-records/", { params });
export const healthApi = () => http.get("/health/");

export const getPolicyApi = () => http.get("/policy/");
export const updatePolicyApi = (payload) => http.post("/policy/", payload);

export const getBanListApi = (params) => http.get("/ban-list/", { params });
export const banIpApi = (payload) => http.post("/ban/", payload);
export const unbanIpApi = (payload) => http.post("/unban/", payload);

export const getAccessLogsApi = (params) => http.get("/access-logs/", { params });
