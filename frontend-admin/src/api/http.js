import axios from "axios";
import { ElMessage } from "element-plus";
import router from "../router";

const http = axios.create({
  baseURL: "/ip-guard/api",
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  timeout: 10000,
});

http.interceptors.response.use(
  (response) => {
    const payload = response.data || {};
    if (payload.code !== 0) {
      ElMessage.error(payload.message || "请求失败");
      return Promise.reject(payload);
    }
    return payload.data;
  },
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      ElMessage.warning("登录状态失效，请重新登录");
      router.push("/login");
    } else if (status === 403) {
      ElMessage.error("没有权限访问该资源");
    } else {
      ElMessage.error(error?.response?.data?.message || "网络异常");
    }
    return Promise.reject(error);
  }
);

export default http;
