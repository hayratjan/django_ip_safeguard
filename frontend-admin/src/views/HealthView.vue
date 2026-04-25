<template>
  <div class="page-card">
    <h3>{{ t('health.title') }}</h3>
    <el-descriptions :column="1" border>
      <el-descriptions-item :label="t('health.service')">{{ data.service }}</el-descriptions-item>
      <el-descriptions-item label="Redis">
        {{ data.redis_ok ? t('health.normal') : t('health.abnormal') }}
        <span v-if="data.redis_ok" class="muted">{{ t('health.latency', { ms: data.redis_latency_ms }) }}</span>
      </el-descriptions-item>
      <el-descriptions-item :label="t('health.provider')">{{ data.provider }}</el-descriptions-item>
      <el-descriptions-item :label="t('health.policyCenter')">{{ data.policy_center_enabled ? t('health.on') : t('health.off') }}</el-descriptions-item>
      <el-descriptions-item :label="t('health.circuitFailures')">
        {{ data.provider_circuit_failures ?? 0 }}
        <span class="muted">{{ t('health.circuitHint') }}</span>
      </el-descriptions-item>
    </el-descriptions>
    <el-button style="margin-top: 12px" :loading="loading" @click="load">{{ t('common.refresh') }}</el-button>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { healthApi } from "../api";

const { t } = useI18n();
const data = ref({});
const loading = ref(false);

const load = async () => {
  loading.value = true;
  try {
    data.value = await healthApi();
  } finally {
    loading.value = false;
  }
};

onMounted(load);
</script>

<style scoped>
.muted {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}
</style>
