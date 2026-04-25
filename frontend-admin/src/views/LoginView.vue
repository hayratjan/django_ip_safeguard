<template>
  <div class="login-page">
    <div class="login-bg" aria-hidden="true" />
    <div class="login-grid" aria-hidden="true" />

    <div class="login-shell">
      <el-card class="login-card" shadow="never">
        <div class="login-brand">
          <img class="login-logo" :src="logoUrl" alt="Django IP Safeguard" width="72" height="72" />
          <h1 class="login-title">IP Guard</h1>
          <p class="login-sub">企业运营控制台 · 安全策略与审计</p>
        </div>

        <el-form :model="form" label-position="top" class="login-form" @submit.prevent="onLogin">
          <el-form-item label="用户名">
            <el-input
              v-model="form.username"
              size="large"
              placeholder="请输入后台账号"
              clearable
              autocomplete="username"
            />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="form.password"
              type="password"
              size="large"
              placeholder="请输入密码"
              show-password
              autocomplete="current-password"
              @keyup.enter="onLogin"
            />
          </el-form-item>
          <el-button type="primary" size="large" :loading="loading" class="login-btn" native-type="submit" @click="onLogin">
            登录
          </el-button>
        </el-form>

        <p class="login-foot">需具备 Django <strong>Staff</strong> 权限；会话与 CSRF 由服务端校验。</p>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";
import { getCsrf, loginApi } from "../api";
import { useAuthStore } from "../stores/auth";
// 与仓库根目录 assets 品牌一致
import logoUrl from "../../../assets/logo.svg?url";

const router = useRouter();
const store = useAuthStore();
const loading = ref(false);
const form = reactive({ username: "", password: "" });

const onLogin = async () => {
  loading.value = true;
  try {
    await getCsrf();
    await loginApi(form);
    await store.fetchMe();
    ElMessage.success("登录成功");
    router.push("/dashboard");
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

.login-foot strong {
  color: #0f766e;
  font-weight: 600;
}
</style>
