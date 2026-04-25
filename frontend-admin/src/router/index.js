import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

const routes = [
  { path: "/login", component: () => import("../views/LoginView.vue"), meta: { public: true } },
  {
    path: "/",
    component: () => import("../layouts/AppLayout.vue"),
    children: [
      { path: "", redirect: "/dashboard" },
      { path: "dashboard", component: () => import("../views/DashboardView.vue") },
      { path: "policy", component: () => import("../views/PolicyView.vue") },
      { path: "ban", component: () => import("../views/BanManagementView.vue") },
      { path: "logs", component: () => import("../views/AccessLogsView.vue") },
      { path: "health", component: () => import("../views/HealthView.vue") },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const store = useAuthStore();
  if (!store.loaded) {
    await store.fetchMe();
  }
  if (to.meta.public) {
    return true;
  }
  if (!store.user) {
    return "/login";
  }
  return true;
});

export default router;
