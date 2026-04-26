<template>
  <div class="login-page">
    <div class="login-bg" aria-hidden="true">
      <div class="bg-orb orb-1" />
      <div class="bg-orb orb-2" />
      <div class="bg-orb orb-3" />
    </div>
    <div class="login-grid" aria-hidden="true" />
    <div class="floating-particles" aria-hidden="true">
      <span v-for="i in 12" :key="i" class="particle" :style="getParticleStyle(i)" />
    </div>

    <div class="login-shell">
      <el-card class="login-card" shadow="never">
        <div class="login-brand">
          <div class="logo-wrapper">
            <img class="login-logo" :src="logoUrl" alt="Django IP Safeguard" width="72" height="72" />
            <div class="logo-glow" />
          </div>
          <h1 class="login-title">
            <span class="title-highlight">IP</span> Guard
          </h1>
          <p class="login-sub">{{ t('login.subtitle') }}</p>
        </div>

        <div class="login-lang-row">
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
        </div>

        <template v-if="!twoFARequired">
          <el-form :model="form" label-position="top" class="login-form" @submit.prevent="onLogin">
            <el-form-item :label="t('login.loginMode')">
              <el-radio-group v-model="loginMode" size="large" class="mode-radio-group">
                <el-radio-button label="session">{{ t('login.sessionMode') }}</el-radio-button>
                <el-radio-button label="jwt">{{ t('login.jwtMode') }}</el-radio-button>
                <el-radio-button label="apikey">{{ t('login.apiKeyMode') }}</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <template v-if="loginMode !== 'apikey'">
              <el-form-item :label="t('login.username')">
                <el-input
                  v-model="form.username"
                  size="large"
                  :placeholder="t('login.usernamePlaceholder')"
                  clearable
                  autocomplete="username"
                />
              </el-form-item>
              <el-form-item :label="t('login.password')">
                <el-input
                  v-model="form.password"
                  type="password"
                  size="large"
                  :placeholder="t('login.passwordPlaceholder')"
                  show-password
                  autocomplete="current-password"
                  @keyup.enter="onLogin"
                />
              </el-form-item>
            </template>
            <template v-else>
              <el-alert
                :title="t('login.apiKeyHint')"
                type="info"
                show-icon
                :closable="false"
                style="margin-bottom: 16px"
                class="custom-alert"
              />
              <el-form-item :label="t('login.apiKeyMode')">
                <el-input
                  v-model="apiKeyForm.api_key"
                  size="large"
                  :placeholder="t('login.apiKeyPlaceholder')"
                  clearable
                  autocomplete="off"
                  @keyup.enter="onApiKeyLogin"
                />
              </el-form-item>
            </template>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              class="login-btn"
              native-type="submit"
              @click="loginMode === 'apikey' ? onApiKeyLogin() : onLogin()"
            >
              {{ t('login.submit') }}
            </el-button>
          </el-form>
        </template>

        <template v-else>
          <el-form :model="twoFAForm" label-position="top" class="login-form" @submit.prevent="on2FAVerify">
            <el-alert
              :title="t('login.twoFARequired')"
              type="info"
              show-icon
              :closable="false"
              style="margin-bottom: 20px"
              class="custom-alert"
            />
            <p style="margin: 0 0 16px; color: #606266; font-size: 14px">
              {{ t('login.twoFAHint') }}
            </p>
            <el-form-item :label="t('userSettings.verificationCode')">
              <el-input
                v-model="twoFAForm.code"
                size="large"
                :placeholder="t('userSettings.enterCode')"
                maxlength="6"
                clearable
                @keyup.enter="on2FAVerify"
              />
            </el-form-item>
            <el-button type="primary" size="large" :loading="twoFALoading" class="login-btn" native-type="submit" @click="on2FAVerify">
              {{ t('login.twoFASubmit') }}
            </el-button>
            <el-button size="large" class="login-btn cancel-btn" style="margin-top: 8px; margin-left: 0" @click="on2FACancel">
              {{ t('common.cancel') }}
            </el-button>
          </el-form>
        </template>

        <div class="login-foot">
          <svg class="foot-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L3 7V12C3 17.55 6.84 22.74 12 24C17.16 22.74 21 17.55 21 12V7L12 2Z" fill="currentColor" opacity="0.6"/>
          </svg>
          <span>{{ t('login.footNote') }}</span>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";
import { clearJwtTokens, getCsrf, jwtLoginApi, loginApi, setJwtTokens, twoFactorLoginVerifyApi, apiKeyLoginApi } from "../api";
import { useAuthStore } from "../stores/auth";
import { useI18nStore } from "../stores/i18n";
import logoUrl from "../assets/logo.svg?url";

const { t } = useI18n();
const router = useRouter();
const store = useAuthStore();
const i18nStore = useI18nStore();
const loading = ref(false);
const twoFALoading = ref(false);
const loginMode = ref("session");
const twoFARequired = ref(false);
const form = reactive({ username: "", password: "" });
const twoFAForm = reactive({ code: "" });
const apiKeyForm = reactive({ api_key: "" });

const currentLangLabel = computed(() => {
  const lang = i18nStore.languages.find((l) => l.code === i18nStore.currentLocale);
  return lang ? lang.name : i18nStore.currentLocale;
});

const getParticleStyle = (index) => {
  const size = Math.random() * 6 + 2;
  const delay = Math.random() * 8;
  const duration = Math.random() * 10 + 15;
  const left = (index / 12) * 100;
  const top = Math.random() * 100;
  return {
    width: `${size}px`,
    height: `${size}px`,
    left: `${left}%`,
    top: `${top}%`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`,
  };
};

const onLangChange = (locale) => {
  i18nStore.switchLocale(locale);
};

const onLogin = async () => {
  loading.value = true;
  try {
    await getCsrf();
    let data;
    if (loginMode.value === "jwt") {
      clearJwtTokens();
      data = await jwtLoginApi(form);
      if (data["2fa_required"]) {
        twoFARequired.value = true;
        return;
      }
      setJwtTokens(data.access_token, data.refresh_token);
    } else {
      clearJwtTokens();
      data = await loginApi(form);
      if (data["2fa_required"]) {
        twoFARequired.value = true;
        return;
      }
    }
    await store.fetchMe();
    ElMessage.success(t('auth.loginSuccess'));
    router.push("/dashboard");
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || t('common.failed'));
  } finally {
    loading.value = false;
  }
};

const on2FAVerify = async () => {
  if (!twoFAForm.code.trim()) {
    ElMessage.warning(t('userSettings.enterCode'));
    return;
  }
  twoFALoading.value = true;
  try {
    const data = await twoFactorLoginVerifyApi({
      code: twoFAForm.code,
      login_mode: loginMode.value,
    });
    if (loginMode.value === "jwt" && data.access_token) {
      setJwtTokens(data.access_token, data.refresh_token);
    }
    twoFARequired.value = false;
    twoFAForm.code = "";
    await store.fetchMe();
    ElMessage.success(t('auth.loginSuccess'));
    router.push("/dashboard");
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || t('common.failed'));
  } finally {
    twoFALoading.value = false;
  }
};

const on2FACancel = () => {
  twoFARequired.value = false;
  twoFAForm.code = "";
};

const onApiKeyLogin = async () => {
  if (!apiKeyForm.api_key.trim()) {
    ElMessage.warning(t('login.apiKeyPlaceholder'));
    return;
  }
  loading.value = true;
  try {
    await getCsrf();
    clearJwtTokens();
    const data = await apiKeyLoginApi({
      api_key: apiKeyForm.api_key.trim(),
      login_mode: "jwt",
    });
    if (data.access_token) {
      setJwtTokens(data.access_token, data.refresh_token);
    }
    apiKeyForm.api_key = "";
    await store.fetchMe();
    ElMessage.success(t('auth.loginSuccess'));
    router.push("/dashboard");
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || t('common.failed'));
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  overflow: hidden;
  background: linear-gradient(145deg, #0b3c5d 0%, #0f766e 42%, #134e4a 100%);
}

.login-bg {
  position: absolute;
  inset: -20%;
  pointer-events: none;
}

.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.6;
  animation: float 20s ease-in-out infinite;
}

.orb-1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(34, 197, 94, 0.35) 0%, transparent 70%);
  top: -15%;
  left: -10%;
  animation-delay: 0s;
}

.orb-2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(147, 197, 253, 0.3) 0%, transparent 70%);
  top: 50%;
  right: -10%;
  animation-delay: -7s;
}

.orb-3 {
  width: 350px;
  height: 350px;
  background: radial-gradient(circle, rgba(16, 185, 129, 0.4) 0%, transparent 70%);
  bottom: -10%;
  left: 30%;
  animation-delay: -14s;
}

@keyframes float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  25% {
    transform: translate(30px, -30px) scale(1.05);
  }
  50% {
    transform: translate(-20px, 20px) scale(0.95);
  }
  75% {
    transform: translate(20px, 30px) scale(1.02);
  }
}

.login-grid {
  position: absolute;
  inset: 0;
  opacity: 0.06;
  background-image: linear-gradient(rgba(255, 255, 255, 1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 1) 1px, transparent 1px);
  background-size: 48px 48px;
  pointer-events: none;
}

.floating-particles {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.particle {
  position: absolute;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 50%;
  animation: particleFloat linear infinite;
  opacity: 0;
}

@keyframes particleFloat {
  0% {
    opacity: 0;
    transform: translateY(100vh) scale(0);
  }
  10% {
    opacity: 0.8;
  }
  90% {
    opacity: 0.8;
  }
  100% {
    opacity: 0;
    transform: translateY(-100px) scale(1);
  }
}

.login-shell {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 460px;
}

.login-card {
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  box-shadow:
    0 8px 32px rgba(11, 60, 93, 0.2),
    0 24px 80px rgba(15, 118, 110, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.login-card:hover {
  transform: translateY(-4px);
  box-shadow:
    0 12px 40px rgba(11, 60, 93, 0.25),
    0 32px 100px rgba(15, 118, 110, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
}

.login-card :deep(.el-card__body) {
  padding: 40px 44px 32px;
}

.login-brand {
  text-align: center;
  margin-bottom: 32px;
}

.logo-wrapper {
  position: relative;
  display: inline-block;
}

.login-logo {
  display: inline-block;
  border-radius: 20px;
  box-shadow:
    0 12px 32px rgba(11, 60, 93, 0.25),
    0 4px 12px rgba(15, 118, 110, 0.2);
  transition: transform 0.3s ease;
}

.login-logo:hover {
  transform: scale(1.05) rotate(3deg);
}

.logo-glow {
  position: absolute;
  inset: -20px;
  background: radial-gradient(circle, rgba(34, 197, 94, 0.3) 0%, transparent 70%);
  border-radius: 50%;
  z-index: -1;
  animation: pulse 3s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.5;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.1);
  }
}

.login-title {
  margin: 20px 0 8px;
  font-size: 32px;
  font-weight: 800;
  letter-spacing: 0.02em;
  color: #0f172a;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.title-highlight {
  background: linear-gradient(135deg, #0f766e 0%, #059669 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.login-sub {
  margin: 0;
  font-size: 14px;
  color: #64748b;
  line-height: 1.6;
  font-weight: 500;
}

.login-lang-row {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

.lang-switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #64748b;
  padding: 6px 12px;
  border-radius: 8px;
  transition: all 0.2s ease;
}
.lang-switch:hover {
  color: #0f766e;
  background: rgba(15, 118, 110, 0.08);
}
.lang-switch .el-icon {
  width: 16px;
  height: 16px;
}
.lang-label {
  font-size: 13px;
  font-weight: 500;
}

.login-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: #374151;
  font-size: 14px;
  padding-bottom: 8px;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: 12px;
  box-shadow: 0 0 0 1px #e5e7eb inset;
  transition: all 0.2s ease;
}

.login-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #0f766e inset;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px #0f766e inset;
}

.login-form :deep(.el-input__inner) {
  font-size: 15px;
}

.mode-radio-group {
  width: 100%;
  display: flex;
}

.mode-radio-group :deep(.el-radio-button__inner) {
  border-radius: 10px;
  margin: 0;
  border: 1px solid #e5e7eb;
  transition: all 0.2s ease;
}

.mode-radio-group :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: linear-gradient(135deg, #0f766e 0%, #059669 100%);
  border-color: #0f766e;
  box-shadow: 0 4px 12px rgba(15, 118, 110, 0.3);
}

.login-btn {
  width: 100%;
  margin-top: 16px;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.04em;
  border-radius: 12px;
  background: linear-gradient(135deg, #0f766e 0%, #059669 100%);
  border: none;
  box-shadow: 0 4px 16px rgba(15, 118, 110, 0.35);
  transition: all 0.3s ease;
  overflow: hidden;
  position: relative;
}

.login-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s ease;
}

.login-btn:hover::before {
  left: 100%;
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(15, 118, 110, 0.4);
}

.login-btn:active {
  transform: translateY(0);
}

.cancel-btn {
  background: #f3f4f6;
  color: #6b7280;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.cancel-btn:hover {
  background: #e5e7eb;
  color: #374151;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.custom-alert {
  border-radius: 12px;
  border: 1px solid rgba(15, 118, 110, 0.2);
  background: rgba(15, 118, 110, 0.05);
}

.custom-alert :deep(.el-alert__title) {
  font-weight: 500;
}

.login-foot {
  margin: 28px 0 0;
  font-size: 12px;
  line-height: 1.7;
  color: #9ca3af;
  text-align: center;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 8px;
}

.foot-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  margin-top: 2px;
  color: #0f766e;
}

@media (max-width: 480px) {
  .login-card :deep(.el-card__body) {
    padding: 28px 24px 24px;
  }

  .login-title {
    font-size: 26px;
  }

  .mode-radio-group {
    flex-wrap: wrap;
  }

  .mode-radio-group :deep(.el-radio-button) {
    flex: 1 1 auto;
    min-width: 80px;
  }
}
</style>
