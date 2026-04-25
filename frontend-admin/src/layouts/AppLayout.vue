<template>
  <el-container style="height: 100%">
    <el-aside width="220px">
      <el-menu router :default-active="$route.path">
        <el-menu-item v-if="can('django_ip_safeguard.view_ipaccesslog')" index="/dashboard">{{ t('nav.dashboard') }}</el-menu-item>
        <el-menu-item v-if="can('django_ip_safeguard.view_ipguardpolicy')" index="/policy">{{ t('nav.policy') }}</el-menu-item>
        <el-menu-item v-if="can('django_ip_safeguard.view_ipbanrecord')" index="/ban">{{ t('nav.ban') }}</el-menu-item>
        <el-menu-item v-if="can('django_ip_safeguard.view_ipaccesslog')" index="/logs">{{ t('nav.logs') }}</el-menu-item>
        <el-menu-item v-if="can('django_ip_safeguard.view_ipguardpolicy')" index="/health">{{ t('nav.health') }}</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="display: flex; justify-content: space-between; align-items: center">
        <div>{{ t('header.title') }}</div>
        <div style="display: flex; align-items: center; gap: 12px">
          <el-dropdown trigger="click" @command="onLangChange">
            <span class="lang-switch">
              <el-icon><svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M512 64a448 448 0 1 0 448 448A448 448 0 0 0 512 64zm0 819.2a371.2 371.2 0 1 1 371.2-371.2A371.2 371.2 0 0 1 512 883.2z"/><path fill="currentColor" d="M510.4 179.2a339.2 339.2 0 0 0-281.6 150.4h563.2A339.2 339.2 0 0 0 510.4 179.2zM512 844.8a384 384 0 0 0 281.6-121.6H230.4A384 384 0 0 0 512 844.8zM196.8 460.8a371.2 371.2 0 0 0 0 102.4h630.4a371.2 371.2 0 0 0 0-102.4z"/></svg></el-icon>
              <span class="lang-label">{{ currentLangLabel }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="lang in i18nStore.languages" :key="lang.code" :command="lang.code" :class="{ 'is-active': lang.code === i18nStore.currentLocale }">
                  {{ lang.name }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <span class="user-label">{{ authStore.user?.username || "—" }}</span>
          <span class="group-label">{{ userGroupsText }}</span>
          <el-button size="small" @click="onLogout">{{ t('header.logout') }}</el-button>
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
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";
import { clearJwtTokens, jwtLogoutApi, logoutApi } from "../api";
import { useAuthStore } from "../stores/auth";
import { useI18nStore } from "../stores/i18n";

const { t } = useI18n();
const router = useRouter();
const authStore = useAuthStore();
const i18nStore = useI18nStore();
const can = (perm) => authStore.hasPerm(perm);

const currentLangLabel = computed(() => {
  const lang = i18nStore.languages.find((l) => l.code === i18nStore.currentLocale);
  return lang ? lang.name : i18nStore.currentLocale;
});

const userGroupsText = computed(() => {
  const groups = authStore.user?.groups || [];
  return groups.length ? `${t('header.group')}: ${groups.join(", ")}` : `${t('header.group')}: ${t('header.noGroup')}`;
});

const onLangChange = (locale) => {
  i18nStore.switchLocale(locale);
};

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
  ElMessage.success(t('auth.logoutSuccess'));
  router.push("/login");
};
</script>

<style scoped>
.lang-switch {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  font-size: 13px;
  color: #606266;
}
.lang-switch:hover {
  color: #409eff;
}
.lang-switch .el-icon {
  width: 16px;
  height: 16px;
}
.lang-label {
  font-size: 13px;
}
.user-label {
  font-size: 13px;
  color: #606266;
}
.group-label {
  font-size: 12px;
  color: #909399;
}
</style>
