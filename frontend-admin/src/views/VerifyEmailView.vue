<template>
  <div class="verify-email-page">
    <el-card class="verify-card">
      <div v-if="loading" class="loading-state">
        <el-icon class="is-loading" style="font-size: 48px; color: var(--el-color-primary)"><Loading /></el-icon>
        <p>{{ t('common.loading') }}...</p>
      </div>
      <div v-else-if="success" class="success-state">
        <el-icon style="font-size: 64px; color: #67c23a; margin-bottom: 16px"><SuccessFilled /></el-icon>
        <h2>{{ t('userSettings.emailVerified') }}</h2>
        <p>{{ t('userSettings.emailChangeHint') }}</p>
        <el-button type="primary" @click="goToLogin">{{ t('common.goToLogin') || '前往登录' }}</el-button>
      </div>
      <div v-else class="error-state">
        <el-icon style="font-size: 64px; color: #f56c6c; margin-bottom: 16px"><CircleCloseFilled /></el-icon>
        <h2>{{ errorTitle }}</h2>
        <p>{{ errorMessage }}</p>
        <el-button type="primary" @click="goToLogin">{{ t('common.goToLogin') || '前往登录' }}</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { SuccessFilled, CircleCloseFilled, Loading } from '@element-plus/icons-vue';
import { verifyEmailApi } from '@/api';
import { ElMessage } from 'element-plus';

const { t } = useI18n();
const router = useRouter();
const route = useRoute();

const loading = ref(true);
const success = ref(false);
const errorTitle = ref('');
const errorMessage = ref('');

async function verifyEmail() {
  const token = route.query.token;
  if (!token) {
    loading.value = false;
    errorTitle.value = t('common.invalidParameter') || '无效参数';
    errorMessage.value = t('verifyEmail.missingToken') || '缺少验证令牌';
    return;
  }

  try {
    const res = await verifyEmailApi(token);
    loading.value = false;
    success.value = true;
    ElMessage.success(res.message || t('userSettings.emailVerified'));
  } catch (e) {
    loading.value = false;
    errorTitle.value = t('verifyEmail.verifyFailed') || '验证失败';
    errorMessage.value = e.response?.data?.message || e.message || t('verifyEmail.invalidToken') || '验证链接无效或已过期';
  }
}

function goToLogin() {
  router.push('/login');
}

onMounted(() => {
  verifyEmail();
});
</script>

<style scoped>
.verify-email-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.verify-card {
  width: 100%;
  max-width: 420px;
  text-align: center;
  border-radius: 12px;
}

.loading-state,
.success-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
}

h2 {
  margin: 16px 0 8px;
  color: #303133;
}

p {
  color: #606266;
  margin-bottom: 24px;
}
</style>
