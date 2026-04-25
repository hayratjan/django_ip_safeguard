<template>
  <div class="page-card">
    <h3>健康状态</h3>
    <el-descriptions :column="1" border>
      <el-descriptions-item label="服务">{{ data.service }}</el-descriptions-item>
      <el-descriptions-item label="Redis">
        {{ data.redis_ok ? "正常" : "异常" }}
        <span v-if="data.redis_ok" class="muted">（延迟约 {{ data.redis_latency_ms }} ms）</span>
      </el-descriptions-item>
      <el-descriptions-item label="Provider">{{ data.provider }}</el-descriptions-item>
      <el-descriptions-item label="策略中心">{{ data.policy_center_enabled ? "开启" : "关闭" }}</el-descriptions-item>
      <el-descriptions-item label="Provider 熔断累计失败次数">
        {{ data.provider_circuit_failures ?? 0 }}
        <span class="muted">（Redis 计数，连续失败触发熔断时使用）</span>
      </el-descriptions-item>
    </el-descriptions>
    <el-button style="margin-top: 12px" :loading="loading" @click="load">刷新</el-button>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { healthApi } from "../api";

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
