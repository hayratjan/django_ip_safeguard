import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

const routes = [
  { path: "/login", component: () => import("../views/LoginView.vue"), meta: { public: true } },
  {
    path: "/",
    component: () => import("../layouts/AppLayout.vue"),
    children: [
      { path: "", redirect: "/dashboard" },
      { path: "dashboard", component: () => import("../views/DashboardView.vue"), meta: { perm: "django_ip_safeguard.view_ipaccesslog" } },
      { path: "policy", component: () => import("../views/PolicyView.vue"), meta: { perm: "django_ip_safeguard.view_ipguardpolicy" } },
      { path: "ban", component: () => import("../views/BanManagementView.vue"), meta: { perm: "django_ip_safeguard.view_ipbanrecord" } },
      { path: "logs", component: () => import("../views/AccessLogsView.vue"), meta: { perm: "django_ip_safeguard.view_ipaccesslog" } },
      { path: "health", component: () => import("../views/HealthView.vue"), meta: { perm: "django_ip_safeguard.view_ipguardpolicy" } },
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
  const fallbackRoutes = ["/dashboard", "/policy", "/ban", "/logs", "/health"];
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
