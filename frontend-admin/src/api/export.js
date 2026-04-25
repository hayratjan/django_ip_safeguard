import axios from "axios";
import { JWT_ACCESS_KEY } from "./http";

/**
 * 导出审计日志 CSV（不走统一 JSON 拦截器，直接拉取文件流；JWT 模式需显式带 Bearer）。
 */
export const downloadAccessLogsCsv = async (params) => {
  const token = localStorage.getItem(JWT_ACCESS_KEY);
  const headers = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const res = await axios.get("/ip-guard/api/access-logs/export/", {
    params,
    withCredentials: true,
    headers,
    responseType: "blob",
    timeout: 120000,
  });
  const blob = new Blob([res.data], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `ip_guard_access_logs_${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
};
