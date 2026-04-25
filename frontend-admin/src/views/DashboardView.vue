<template>
  <div class="page-card">
    <h3>运营仪表盘</h3>
    <el-space style="margin-bottom: 12px">
      <el-button :loading="loading" @click="load">刷新</el-button>
    </el-space>
    <el-skeleton :loading="loading" animated>
      <el-row :gutter="12" style="margin-bottom: 16px">
        <el-col :span="6"><el-statistic title="24h 总请求" :value="data.total_count_24h || 0" /></el-col>
        <el-col :span="6"><el-statistic title="24h 拦截" :value="data.block_count_24h || 0" /></el-col>
        <el-col :span="6"><el-statistic title="24h 放行" :value="data.allow_count_24h || 0" /></el-col>
        <el-col :span="6">
          <el-statistic title="24h 拦截率" :value="(data.block_rate_24h || 0) * 100" suffix="%" :precision="2" />
        </el-col>
      </el-row>
      <el-row :gutter="12" style="margin-bottom: 16px">
        <el-col :span="12">
          <h4 class="sub">决策分布（24h）</h4>
          <el-table :data="decisionRows" size="small" max-height="200">
            <el-table-column prop="k" label="决策" width="100" />
            <el-table-column prop="v" label="次数" />
          </el-table>
        </el-col>
        <el-col :span="12">
          <h4 class="sub">按小时趋势（24h）</h4>
          <el-table :data="data.hourly_trend || []" size="small" max-height="240">
            <el-table-column prop="bucket" label="小时" min-width="160" />
            <el-table-column prop="total" label="总请求" width="90" />
            <el-table-column prop="blocked" label="拦截" width="90" />
          </el-table>
        </el-col>
      </el-row>
      <el-row :gutter="12" style="margin-bottom: 16px">
        <el-col :span="12">
          <h4 class="sub">高风险 IP（拦截 Top10）</h4>
          <el-table :data="data.top_risk_ips || []" size="small">
            <el-table-column prop="ip" label="IP" />
            <el-table-column prop="count" label="次数" width="100" />
          </el-table>
        </el-col>
        <el-col :span="12">
          <h4 class="sub">国家分布 Top10</h4>
          <el-table :data="data.country_distribution || []" size="small">
            <el-table-column prop="country_code" label="国家" />
            <el-table-column prop="count" label="次数" width="100" />
          </el-table>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="12">
          <h4 class="sub">热门路径 Top10</h4>
          <el-table :data="data.top_paths || []" size="small">
            <el-table-column prop="path" label="路径" show-overflow-tooltip />
            <el-table-column prop="count" label="次数" width="100" />
          </el-table>
        </el-col>
        <el-col :span="12">
          <h4 class="sub">拦截原因 Top10</h4>
          <el-table :data="data.top_block_reasons || []" size="small">
            <el-table-column prop="reason" label="原因" show-overflow-tooltip />
            <el-table-column prop="count" label="次数" width="100" />
          </el-table>
        </el-col>
      </el-row>
    </el-skeleton>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { dashboardApi } from "../api";

const data = ref({});
const loading = ref(false);

const decisionRows = computed(() => {
  const dist = data.value.decision_distribution || {};
  return Object.keys(dist).map((k) => ({ k, v: dist[k] }));
});

const load = async () => {
  loading.value = true;
  try {
    data.value = await dashboardApi();
  } finally {
    loading.value = false;
  }
};

onMounted(load);
</script>

<style scoped>
.sub {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: #606266;
}
</style>
