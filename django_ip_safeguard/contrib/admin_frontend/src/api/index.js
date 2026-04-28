import http, { clearJwtTokens, setJwtTokens } from "./http";

export { clearJwtTokens, setJwtTokens };

export const getCsrf = () => http.get("/auth/csrf/");
export const loginApi = (payload) => http.post("/auth/login/", payload);
export const jwtLoginApi = (payload) => http.post("/auth/jwt/login/", payload);
export const jwtRefreshApi = (payload) => http.post("/auth/jwt/refresh/", payload);
export const jwtLogoutApi = () => http.post("/auth/jwt/logout/");
export const logoutApi = () => http.post("/auth/logout/");
export const meApi = () => http.get("/auth/me/");

export const changePasswordApi = (payload) => http.post("/auth/change-password/", payload);
export const changeEmailApi = (payload) => http.post("/auth/change-email/", payload);
export const verifyEmailApi = (token) => http.get(`/auth/verify-email/?token=${encodeURIComponent(token)}`);
export const userProfileApi = () => http.get("/auth/profile/");
export const twoFactorStatusApi = () => http.get("/auth/2fa/status/");
export const twoFactorSetupApi = () => http.post("/auth/2fa/setup/");
export const twoFactorVerifyApi = (payload) => http.post("/auth/2fa/verify/", payload);
export const twoFactorDisableApi = (payload) => http.post("/auth/2fa/disable/", payload);
export const twoFactorLoginVerifyApi = (payload) => http.post("/auth/2fa/login-verify/", payload);

export const apiKeyLoginApi = (payload) => http.post("/auth/api-key/login/", payload);
export const apiKeyListApi = () => http.get("/auth/api-key/list/");
export const apiKeyCreateApi = (payload) => http.post("/auth/api-key/create/", payload);
export const apiKeyRevokeApi = (payload) => http.post("/auth/api-key/revoke/", payload);
export const apiKeyLogsApi = (payload) => http.post("/auth/api-key/logs/", payload);

export const dashboardApi = () => http.get("/dashboard/");
export const recentRecordsApi = (params) => http.get("/recent-records/", { params });
export const healthApi = () => http.get("/health/");
export const userStatsChartApi = (params) => http.get("/user-stats-chart/", { params });

export const getPolicyApi = () => http.get("/policy/");
export const updatePolicyApi = (payload) => http.post("/policy/", payload);

export const metricsApi = () => http.get("/metrics/");
export const metricsResetApi = () => http.post("/metrics/reset/");
export const listPoliciesApi = () => http.get("/policies/");
export const createPolicyApi = (payload) => http.post("/policies/", payload);
export const getPolicyByNameApi = (name) => http.get(`/policies/${encodeURIComponent(name)}/`);
export const updatePolicyByNameApi = (name, payload) =>
  http.post(`/policies/${encodeURIComponent(name)}/`, payload);
export const listPolicySnapshotsApi = (params) => http.get("/policy/snapshots/", { params });
export const rollbackPolicySnapshotApi = (snapshotId) =>
  http.post(`/policy/snapshots/${snapshotId}/rollback/`);

export const getGeoPoolsStatusApi = () => http.get("/geo-pools/status/");
export const syncGeoPoolsApi = () => http.post("/geo-pools/sync/");

export const getBanListApi = (params) => http.get("/ban-list/", { params });
export const banIpApi = (payload) => http.post("/ban/", payload);
export const unbanIpApi = (payload) => http.post("/unban/", payload);

export const getAccessLogsApi = (params) => http.get("/access-logs/", { params });
export const getSecurityAuditLogsApi = (params) => http.get("/security-audit-logs/", { params });

export const i18nLangListApi = () => http.get("/i18n/languages/");
export const i18nLangSwitchApi = (payload) => http.post("/i18n/switch/", payload);

export const getSystemSettingsApi = () => http.get("/system-settings/");
export const updateSystemSettingsApi = (payload) => http.post("/system-settings/", payload);

export const getScheduledTaskListApi = (params) => http.get("/scheduled-tasks/", { params });
export const createScheduledTaskApi = (payload) => http.post("/scheduled-tasks/", payload);
export const getScheduledTaskDetailApi = (taskId) => http.get(`/scheduled-tasks/${taskId}/`);
export const updateScheduledTaskApi = (taskId, payload) => http.put(`/scheduled-tasks/${taskId}/`, payload);
export const deleteScheduledTaskApi = (taskId) => http.delete(`/scheduled-tasks/${taskId}/`);
export const runScheduledTaskApi = (taskId) => http.post(`/scheduled-tasks/${taskId}/run/`);

export const listDjangoUsersApi = (params) => http.get("/admin/users/", { params });
export const createDjangoUserApi = (payload) => http.post("/admin/users/", payload);
export const patchDjangoUserApi = (userId, payload) => http.patch(`/admin/users/${userId}/`, payload);
export const listDjangoGroupsApi = () => http.get("/admin/groups/");
