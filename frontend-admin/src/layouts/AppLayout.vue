<template>
  <el-container style="height: 100%" class="app-layout">
    <el-aside width="220px" class="sidebar">
      <div class="sidebar-logo" @click="router.push('/dashboard')">
        <img :src="logoUrl" alt="Logo" class="sidebar-logo-img" />
        <span class="sidebar-logo-text">IP Safeguard</span>
      </div>
      <el-menu router :default-active="$route.path">
        <el-menu-item v-if="can('django_ip_safeguard.view_ipaccesslog')" index="/dashboard">
          <el-icon><svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M924.8 385.6a446.7 446.7 0 0 0-96-142.4 446.7 446.7 0 0 0-142.4-96C631.1 123.8 572.5 112 512 112s-119.1 11.8-174.4 35.2a446.7 446.7 0 0 0-142.4 96 446.7 446.7 0 0 0-96 142.4C75.8 440.9 64 499.5 64 560c0 132.7 58.2 258.2 160 346.1V928a32 32 0 0 0 32 32h512a32 32 0 0 0 32-32v-21.9c101.8-87.9 160-213.4 160-346.1 0-60.5-11.8-119.1-35.2-174.4zM512 880c-176.7 0-320-143.3-320-320s143.3-320 320-320 320 143.3 320 320-143.3 320-320 320z"/></svg></el-icon>
          {{ t('nav.dashboard') }}
        </el-menu-item>
        <el-menu-item v-if="can('django_ip_safeguard.view_ipguardpolicy')" index="/policy">
          <el-icon><svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M832 464h-68V240c0-70.7-57.3-128-128-128H388c-70.7 0-128 57.3-128 128v224h-68c-17.7 0-32 14.3-32 32v384c0 17.7 14.3 32 32 32h640c17.7 0 32-14.3 32-32V496c0-17.7-14.3-32-32-32zM540 701v53c0 4.4-3.6 8-8 8h-40c-4.4 0-8-3.6-8-8v-53c-12.1-8.7-20-22.9-20-39 0-26.5 21.5-48 48-48s48 21.5 48 48c0 16.1-7.9 30.3-20 39zm152-237H332V240c0-30.9 25.1-56 56-56h248c30.9 0 56 25.1 56 56v224z"/></svg></el-icon>
          {{ t('nav.policy') }}
        </el-menu-item>
        <el-menu-item v-if="can('django_ip_safeguard.view_ipbanrecord')" index="/ban">
          <el-icon><svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372z"/><path fill="currentColor" d="M512 140c-205.4 0-372 166.6-372 372s166.6 372 372 372 372-166.6 372-372-166.6-372-372-372zm193.4 225.7l-210.6 292a31.8 31.8 0 0 1-51.7 0L318.5 484.9c-3.8-5.3 0-12.7 6.5-12.7h46.9c10.3 0 19.9 5 25.9 13.3l71.2 99.5 157.3-218.5c6-8.4 15.7-13.3 25.9-13.3H699c6.5 0 9.9 7.4 6.4 12.5z"/></svg></el-icon>
          {{ t('nav.ban') }}
        </el-menu-item>
        <el-menu-item v-if="can('django_ip_safeguard.view_ipaccesslog')" index="/logs">
          <el-icon><svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M880 112H144c-17.7 0-32 14.3-32 32v736c0 17.7 14.3 32 32 32h736c17.7 0 32-14.3 32-32V144c0-17.7-14.3-32-32-32zm-40 728H184V184h656v656z"/><path fill="currentColor" d="M493 400h108c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8H493c-4.4 0-8 3.6-8 8v48c0 4.4 3.6 8 8 8zm0 144h108c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8H493c-4.4 0-8 3.6-8 8v48c0 4.4 3.6 8 8 8zm0 144h108c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8H493c-4.4 0-8 3.6-8 8v48c0 4.4 3.6 8 8 8zM340 400h48c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8h-48c-4.4 0-8 3.6-8 8v48c0 4.4 3.6 8 8 8zm0 144h48c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8h-48c-4.4 0-8 3.6-8 8v48c0 4.4 3.6 8 8 8zm0 144h48c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8h-48c-4.4 0-8 3.6-8 8v48c0 4.4 3.6 8 8 8z"/></svg></el-icon>
          {{ t('nav.logs') }}
        </el-menu-item>
        <el-menu-item v-if="can('django_ip_safeguard.view_ipguardpolicy')" index="/health">
          <el-icon><svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372z"/><path fill="currentColor" d="M464 336a48 48 0 1 0 96 0 48 48 0 1 0-96 0zm72 112h-48c-4.4 0-8 3.6-8 8v272c0 4.4 3.6 8 8 8h48c4.4 0 8-3.6 8-8V456c0-4.4-3.6-8-8-8z"/></svg></el-icon>
          {{ t('nav.health') }}
        </el-menu-item>
        <el-menu-item v-if="can('django_ip_safeguard.view_ipaccesslog')" index="/user-chart">
          <el-icon><svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M888 792H200V168c0-4.4-3.6-8-8-8h-56c-4.4 0-8 3.6-8 8v688c0 4.4 3.6 8 8 8h752c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8zM305 625l90-128 72 96 120-160 162 232c4 5.7 0 13.5-6.9 13.5H311.8c-6.9 0-10.9-7.8-6.8-13.5z"/></svg></el-icon>
          {{ t('nav.userChart') }}
        </el-menu-item>
        <el-menu-item index="/user-settings">
          <el-icon><svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M858.5 763.6a374 374 0 0 0-80.2-119.6 375.4 375.4 0 0 0-119.6-80.2c-.4-.2-.8-.3-1.2-.5C719.5 518 760 444.5 760 362c0-137-111-248-248-248S264 225 264 362c0 82.5 40.5 156 102.8 201.1-.4.2-.8.3-1.2.5-44.8 18.9-85 46-119.6 80.2a374 374 0 0 0-80.2 119.6A375.3 375.3 0 0 0 136 901.8a8 8 0 0 0 8 8.2h60c4.4 0 7.9-3.5 8-7.8 2-77.2 33-149.5 87.8-204.3 56.7-56.7 132-87.9 212.2-87.9s155.5 31.2 212.2 87.9C779 752.7 810 825 812 902.2c.1 4.4 3.6 7.8 8 7.8h60a8 8 0 0 0 8-8.2c-1-47.8-10.9-94.3-29.5-138.2zM512 560c-109.9 0-200-90.1-200-200s90.1-200 200-200 200 90.1 200 200-90.1 200-200 200z"/></svg></el-icon>
          {{ t('nav.userSettings') }}
        </el-menu-item>
        <el-menu-item v-if="can('django_ip_safeguard.view_ipguardpolicy')" index="/system-settings">
          <el-icon><svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M924.8 625.7l-65.5-56c3.1-19 4.7-38.4 4.7-57.8s-1.6-38.8-4.7-57.8l65.5-56a32.03 32.03 0 0 0 9.3-35.2l-.9-2.6a443.7 443.7 0 0 0-79.7-137.9l-1.8-2.1a32.12 32.12 0 0 0-35.1-9.5l-81.3 28.9c-30-24.6-63.5-44-99.7-57.6l-15.7-85a32.05 32.05 0 0 0-25.8-25.7l-2.7-.5c-52.1-9.4-106.9-9.4-159 0l-2.7.5a32.05 32.05 0 0 0-25.8 25.7l-15.8 85.4a351.4 351.4 0 0 0-99 57.4l-81.9-29.1a32 32 0 0 0-35.1 9.5l-1.8 2.1a446.02 446.02 0 0 0-79.7 137.9l-.9 2.6c-4.5 12.5-.8 26.5 9.3 35.2l66.3 56.6c-3.1 18.8-4.6 38-4.6 57.1 0 19.2 1.5 38.4 4.6 57.1L99 625.5a32.03 32.03 0 0 0-9.3 35.2l.9 2.6c18.1 50.4 44.9 96.9 79.7 137.9l1.8 2.1a32.12 32.12 0 0 0 35.1 9.5l81.9-29.1c29.8 24.5 63.1 43.9 99 57.4l15.8 85.4a32.05 32.05 0 0 0 25.8 25.7l2.7.5c26.2 4.6 53.1 7 79.5 7s53.3-2.4 79.5-7l2.7-.5a32.05 32.05 0 0 0 25.8-25.7l15.7-85a350 350 0 0 0 99.7-57.6l81.3 28.9a32 32 0 0 0 35.1-9.5l1.8-2.1c34.8-41.1 61.6-87.5 79.7-137.9l.9-2.6c4.5-12.3.8-26.2-9.3-35zM512 654c-78.5 0-142-63.5-142-142s63.5-142 142-142 142 63.5 142 142-63.5 142-142 142z"/></svg></el-icon>
          {{ t('nav.systemSettings') }}
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header" style="display: flex; justify-content: space-between; align-items: center">
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
          <el-dropdown trigger="click" @command="onThemeChange">
            <span class="lang-switch">
              <el-icon>
                <svg v-if="themeStore.isDark" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M511.8 832c-176.8 0-320-143.1-320-320 0-176.8 143.2-320 320-320 14.6 0 29 .9 43.2 2.8C517 148.3 452.8 128 384 128c-141.4 0-256 114.6-256 256s114.6 256 256 256c68.8 0 133-20.3 186.8-55.2-1.3 7.6-2 15.4-2 23.2 0 141.4 114.6 256 256 256 7.8 0 15.6-.7 23.2-2C813.3 917.8 672.7 960 512 960c-14.6 0-29-.9-43.2-2.8 1.3-7.6 2-15.4 2-23.2 0-141.4-114.6-256-256-256z"/></svg>
                <svg v-else viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M512 64a448 448 0 1 0 448 448A448 448 0 0 0 512 64zm0 819.2a371.2 371.2 0 1 1 371.2-371.2A371.2 371.2 0 0 1 512 883.2z"/><path fill="currentColor" d="M512 256a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V288a32 32 0 0 1 32-32z"/></svg>
              </el-icon>
              <span class="lang-label">{{ themeStore.actualTheme === 'dark' ? t('header.darkMode') : t('header.lightMode') }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="opt in themeStore.themeOptions" :key="opt.value" :command="opt.value" :class="{ 'is-active': opt.value === themeStore.theme }">
                  {{ opt.label }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-dropdown trigger="click" @command="onUserCommand">
            <span class="lang-switch" style="cursor: pointer">
              <el-icon><svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M858.5 763.6a374 374 0 0 0-80.2-119.6 375.4 375.4 0 0 0-119.6-80.2c-.4-.2-.8-.3-1.2-.5C719.5 518 760 444.5 760 362c0-137-111-248-248-248S264 225 264 362c0 82.5 40.5 156 102.8 201.1-.4.2-.8.3-1.2.5-44.8 18.9-85 46-119.6 80.2a374 374 0 0 0-80.2 119.6A375.3 375.3 0 0 0 136 901.8a8 8 0 0 0 8 8.2h60c4.4 0 7.9-3.5 8-7.8 2-77.2 33-149.5 87.8-204.3 56.7-56.7 132-87.9 212.2-87.9s155.5 31.2 212.2 87.9C779 752.7 810 825 812 902.2c.1 4.4 3.6 7.8 8 7.8h60a8 8 0 0 0 8-8.2c-1-47.8-10.9-94.3-29.5-138.2zM512 560c-109.9 0-200-90.1-200-200s90.1-200 200-200 200 90.1 200 200-90.1 200-200 200z"/></svg></el-icon>
              <span class="lang-label">{{ authStore.user?.username || "—" }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="settings">{{ t('nav.userSettings') }}</el-dropdown-item>
                <el-dropdown-item command="system" v-if="can('django_ip_safeguard.view_ipguardpolicy')">{{ t('nav.systemSettings') }}</el-dropdown-item>
                <el-dropdown-item divided command="logout">{{ t('header.logout') }}</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main-content">
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
import { useThemeStore } from "../stores/theme";
import logoUrl from "../assets/logo.svg?url";

const { t } = useI18n();
const router = useRouter();
const authStore = useAuthStore();
const i18nStore = useI18nStore();
const themeStore = useThemeStore();
const can = (perm) => authStore.hasPerm(perm);

const currentLangLabel = computed(() => {
  const lang = i18nStore.languages.find((l) => l.code === i18nStore.currentLocale);
  return lang ? lang.name : i18nStore.currentLocale;
});

const onLangChange = (locale) => {
  i18nStore.switchLocale(locale);
};

const onThemeChange = (theme) => {
  themeStore.setTheme(theme);
};

const onUserCommand = (command) => {
  if (command === "settings") {
    router.push("/user-settings");
  } else if (command === "system") {
    router.push("/system-settings");
  } else if (command === "logout") {
    onLogout();
  }
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
.app-layout .sidebar {
  border-right: 1px solid var(--ip-border, #dcdfe6);
  overflow-y: auto;
}
.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 18px;
  cursor: pointer;
  border-bottom: 1px solid var(--ip-border, #dcdfe6);
  user-select: none;
}
.sidebar-logo:hover {
  background: var(--el-menu-hover-bg-color, #ecf5ff);
}
.sidebar-logo-img {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  flex-shrink: 0;
}
.sidebar-logo-text {
  font-size: 15px;
  font-weight: 700;
  color: var(--ip-text, #1e293b);
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.app-layout .header {
  border-bottom: 1px solid var(--ip-border, #dcdfe6);
}
.app-layout .main-content {
  background: var(--ip-bg, #f4f6f8);
}
.lang-switch {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  font-size: 13px;
  color: var(--ip-text-secondary, #606266);
}
.lang-switch:hover {
  color: var(--el-color-primary, #409eff);
}
.lang-switch .el-icon {
  width: 16px;
  height: 16px;
}
.lang-label {
  font-size: 13px;
}
</style>
