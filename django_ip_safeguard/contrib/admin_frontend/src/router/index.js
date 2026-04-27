import { createRouter, createWebHistory } from "vue-router";
import { defineAsyncComponent } from "vue";
import { useAuthStore } from "../stores/auth";

const routes = [
  { path: "/login", component: () => import("../views/LoginView.vue"), meta: { public: true } },
  {
    path: "/",
    component: () => import("../layouts/AppLayout.vue"),
    children: [
      { path: "", redirect: "/dashboard" },
      { path: "dashboard", component: () => import("../views/DashboardView.vue"), meta: { perm: "django_ip_safeguard.view_ipaccesslog" } },
      { path: "policy", component: defineAsyncComponent(() => import("../views/PolicyView.vue")), meta: { perm: "django_ip_safeguard.view_ipguardpolicy" } },
      { path: "ban", component: defineAsyncComponent(() => import("../views/BanManagementView.vue")), meta: { perm: "django_ip_safeguard.view_ipbanrecord" } },
      { path: "logs", component: defineAsyncComponent(() => import("../views/AccessLogsView.vue")), meta: { perm: "django_ip_safeguard.view_ipaccesslog" } },
      { path: "health", component: defineAsyncComponent(() => import("../views/HealthView.vue")), meta: { perm: "django_ip_safeguard.view_ipguardpolicy" } },
      { path: "user-settings", component: () => import("../views/UserSettingsView.vue") },
      { path: "user-chart", component: defineAsyncComponent(() => import("../views/UserChartView.vue")), meta: { perm: "django_ip_safeguard.view_ipaccesslog" } },
      { path: "system-settings", component: defineAsyncComponent(() => import("../views/SystemSettingsView.vue")), meta: { perm: "django_ip_safeguard.view_ipguardpolicy" } },
      { path: "scheduled-tasks", component: defineAsyncComponent(() => import("../views/ScheduledTasksView.vue")), meta: { perm: "django_ip_safeguard.view_scheduledtask" } },
      { path: "security-audit", component: defineAsyncComponent(() => import("../views/SecurityAuditView.vue")), meta: { perm: "django_ip_safeguard.view_ipguardpolicy" } },
    ],
  },
  { path: "/verify-email", component: () => import("../views/VerifyEmailView.vue"), meta: { public: true } },
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
  const fallbackRoutes = ["/dashboard", "/policy", "/ban", "/logs", "/health", "/user-settings"];
  const firstAllowed = fallbackRoutes.find((path) => {
    const route = routes[1].children.find((r) => `/${r.path}` === path);
    if (!route?.meta?.perm) return true;
    return store.hasPerm(route.meta.perm);
  }) || "/login";
  const requiredPerm = to.meta?.perm;
  if (requiredPerm && !store.hasPerm(requiredPerm)) {
    return firstAllowed;
  }
  return true;
});

export default router;
