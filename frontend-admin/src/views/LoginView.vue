<template>
  <div class="login-page">
    <div class="login-bg" aria-hidden="true" />
    <div class="login-grid" aria-hidden="true" />

    <div class="login-shell">
      <el-card class="login-card" shadow="never">
        <div class="login-brand">
          <img class="login-logo" :src="logoUrl" alt="Django IP Safeguard" width="72" height="72" />
          <h1 class="login-title">{{ t('login.title') }}</h1>
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
              <el-radio-group v-model="loginMode" size="large">
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
              />
              <el-form-item :label="t('login.apiKeyMode')">
                <el-input
                  v-model="apiKeyForm.api_key"
                  size="large"
                  :placeholder="t('login.apiKeyPlaceholder')"
                  clearable
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
            <el-button size="large" class="login-btn" style="margin-top: 8px; margin-left: 0" @click="on2FACancel">
              {{ t('common.cancel') }}
            </el-button>
          </el-form>
        </template>

        <p class="login-foot">
          {{ t('login.footNote') }}
        </p>
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
  background:
    radial-gradient(ellipse 60% 50% at 20% 10%, rgba(34, 197, 94, 0.22), transparent 55%),
    radial-gradient(ellipse 50% 45% at 85% 75%, rgba(147, 197, 253, 0.18), transparent 50%),
    radial-gradient(circle at 50% 100%, rgba(15, 118, 110, 0.35), transparent 45%);
  pointer-events: none;
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

.login-shell {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
}

.login-card {
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  box-shadow:
    0 4px 24px rgba(11, 60, 93, 0.15),
    0 24px 64px rgba(15, 118, 110, 0.12);
}

.login-card :deep(.el-card__body) {
  padding: 36px 40px 28px;
}

.login-brand {
  text-align: center;
  margin-bottom: 28px;
}

.login-logo {
  display: inline-block;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(11, 60, 93, 0.2);
}

.login-title {
  margin: 16px 0 6px;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #0f172a;
}

.login-sub {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}

.login-lang-row {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

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

.login-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #475569;
}

.login-btn {
  width: 100%;
  margin-top: 8px;
  font-weight: 600;
  letter-spacing: 0.06em;
}

.login-foot {
  margin: 24px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: #94a3b8;
  text-align: center;
}
</style>
