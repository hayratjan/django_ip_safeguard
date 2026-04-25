import http from "./http";

export const getCsrf = () => http.get("/auth/csrf/");
export const loginApi = (payload) => http.post("/auth/login/", payload);
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
