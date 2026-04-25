<template>
  <el-container style="height: 100%">
    <el-aside width="220px">
      <el-menu router :default-active="$route.path">
        <el-menu-item v-if="can('django_ip_safeguard.view_ipaccesslog')" index="/dashboard">仪表盘</el-menu-item>
        <el-menu-item v-if="can('django_ip_safeguard.view_ipguardpolicy')" index="/policy">策略中心</el-menu-item>
        <el-menu-item v-if="can('django_ip_safeguard.view_ipbanrecord')" index="/ban">封禁管理</el-menu-item>
        <el-menu-item v-if="can('django_ip_safeguard.view_ipaccesslog')" index="/logs">审计日志</el-menu-item>
        <el-menu-item v-if="can('django_ip_safeguard.view_ipguardpolicy')" index="/health">健康状态</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="display: flex; justify-content: space-between; align-items: center">
        <div>IP Guard 企业控制台</div>
        <div style="display: flex; align-items: center; gap: 12px">
          <span class="user-label">{{ authStore.user?.username || "—" }}</span>
          <span class="group-label">{{ userGroupsText }}</span>
          <el-button size="small" @click="onLogout">退出登录</el-button>
        </div>
      </el-header>
      <el-main style="background: #f4f6f8">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from "vue";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";
import { clearJwtTokens, jwtLogoutApi, logoutApi } from "../api";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const authStore = useAuthStore();
const can = (perm) => authStore.hasPerm(perm);
const userGroupsText = computed(() => {
  const groups = authStore.user?.groups || [];
  return groups.length ? `组: ${groups.join(", ")}` : "组: 无";
});

const onLogout = async () => {
  try {
    await logoutApi();
  } catch {
    /* 纯 JWT 时无 Session 可忽略 */
  }
  try {
    await jwtLogoutApi();
  } catch {
    /* 无 CSRF 或忽略 */
  }
  clearJwtTokens();
  authStore.clear();
  ElMessage.success("已退出");
  router.push("/login");
};
</script>

<style scoped>
.user-label {
  font-size: 13px;
  color: #606266;
}

.group-label {
  font-size: 12px;
  color: #909399;
}
</style>
