<template>
  <div class="dashboard-page">
    <div class="dash-header">
      <h3 class="dash-title">{{ t('dashboard.title') }}</h3>
      <el-button :loading="loading" type="primary" plain size="small" @click="load">
        <el-icon><svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M771.776 794.88A384 384 0 0 1 128 512h64a320 320 0 0 0 555.712 216.448H654.72a32 32 0 1 1 0-64h149.056a32 32 0 0 1 32 32v148.928a32 32 0 1 1-64 0v-50.56zM276.288 265.344h64.064a32 32 0 0 1 0 64H202.752a32 32 0 0 1-32-32V148.352a32 32 0 1 1 64 0v50.56A384 384 0 0 1 896 512h-64a320 320 0 0 0-555.712-216.448z"/></svg></el-icon>
        {{ t('common.refresh') }}
      </el-button>
    </div>

    <el-skeleton :loading="loading" animated>
      <div class="stats-row">
        <div class="stat-card stat-total" @click="goLogs()">
          <div class="stat-icon">
            <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M192 128v768h640V128H192zm-32-64h704a32 32 0 0 1 32 32v832a32 32 0 0 1-32 32H160a32 32 0 0 1-32-32V96a32 32 0 0 1 32-32zm160 224h384v64H320v-64zm0 160h384v64H320v-64zm0 160h256v64H320v-64z"/></svg>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ data.total_count_24h || 0 }}</span>
            <span class="stat-label">24h 访问总次数</span>
          </div>
        </div>
        <div class="stat-card stat-allow" @click="goLogs('allow')">
          <div class="stat-icon">
            <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M512 64a448 448 0 1 0 448 448A448 448 0 0 0 512 64zm0 819.2a371.2 371.2 0 1 1 371.2-371.2A371.2 371.2 0 0 1 512 883.2zM362.24 534.4l90.56 90.56L661.76 416l45.12 45.12L452.8 715.2l-135.68-135.68z"/></svg>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ data.allow_count_24h || 0 }}</span>
            <span class="stat-label">24h 放行次数</span>
          </div>
        </div>
        <div class="stat-card stat-block" @click="goLogs('block')">
          <div class="stat-icon">
            <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M512 64a448 448 0 1 0 448 448A448 448 0 0 0 512 64zm0 819.2a371.2 371.2 0 1 1 371.2-371.2A371.2 371.2 0 0 1 512 883.2zM288 480h448v64H288z"/></svg>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ data.block_count_24h || 0 }}</span>
            <span class="stat-label">24h 被拦截次数</span>
          </div>
        </div>
        <div class="stat-card stat-rate" @click="goLogs('block')">
          <div class="stat-icon">
            <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M512 896c-212.064 0-384-171.936-384-384S299.936 128 512 128s384 171.936 384 384-171.936 384-384 384zm0-704c-176.448 0-320 143.552-320 320s143.552 320 320 320 320-143.552 320-320-143.552-320-320-320zm0 576c-141.376 0-256-114.624-256-256s114.624-256 256-256 256 114.624 256 256-114.624 256-256 256zm0-448c-106.048 0-192 85.952-192 192s85.952 192 192 192 192-85.952 192-192-85.952-192-192-192zm0 320c-70.688 0-128-57.312-128-128s57.312-128 128-128 128 57.312 128 128-57.312 128-128 128z"/></svg>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ ((data.block_rate_24h || 0) * 100).toFixed(2) }}%</span>
            <span class="stat-label">24h 拦截率</span>
          </div>
        </div>
      </div>

      <div class="map-section">
        <DashboardWorldIpMap :distribution="data.country_distribution || []" @country-click="onCountryClick" />
      </div>

      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="12">
          <div class="section-card">
            <div class="section-header">
              <h4 class="section-title">{{ t('dashboard.highRiskIps') }}</h4>
              <el-button text size="small" @click="goLogs('block')">查看全部 →</el-button>
            </div>
            <el-table :data="data.top_risk_ips || []" size="small" class="clickable-table" @row-click="onRiskIpClick">
              <el-table-column prop="ip" label="IP" />
              <el-table-column prop="count" :label="t('dashboard.count')" width="100" />
            </el-table>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="section-card">
            <div class="section-header">
              <h4 class="section-title">{{ t('dashboard.countryDist') }}</h4>
              <el-button text size="small" @click="goLogs()">查看全部 →</el-button>
            </div>
            <el-table :data="data.country_distribution || []" size="small" class="clickable-table" @row-click="onCountryRowClick">
              <el-table-column prop="country_code" :label="t('dashboard.countryCode')" />
              <el-table-column prop="count" :label="t('dashboard.count')" width="100" />
            </el-table>
          </div>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="12">
          <div class="section-card">
            <div class="section-header">
              <h4 class="section-title">{{ t('dashboard.hotPaths') }}</h4>
            </div>
            <el-table :data="data.top_paths || []" size="small" class="clickable-table" @row-click="onPathClick">
              <el-table-column prop="path" :label="t('dashboard.path')" show-overflow-tooltip />
              <el-table-column prop="count" :label="t('dashboard.count')" width="100" />
            </el-table>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="section-card">
            <div class="section-header">
              <h4 class="section-title">{{ t('dashboard.blockReasons') }}</h4>
            </div>
            <el-table :data="data.top_block_reasons || []" size="small">
              <el-table-column prop="reason" :label="t('dashboard.reason')" show-overflow-tooltip />
              <el-table-column prop="count" :label="t('dashboard.count')" width="100" />
            </el-table>
          </div>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="24">
          <div class="section-card">
            <div class="section-header">
              <h4 class="section-title">{{ t('dashboard.recentRecords') }}</h4>
            </div>
            <DashboardRecentRecords />
          </div>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="12">
          <div class="section-card">
            <h4 class="section-title">{{ t('dashboard.decisionDist') }}</h4>
            <el-table :data="decisionRows" size="small">
              <el-table-column prop="k" :label="t('dashboard.decision')" width="100" />
              <el-table-column prop="v" :label="t('dashboard.count')" />
            </el-table>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="section-card">
            <h4 class="section-title">{{ t('dashboard.hourlyTrend') }}</h4>
            <el-table :data="data.hourly_trend || []" size="small" max-height="240">
              <el-table-column prop="bucket" :label="t('dashboard.hour')" min-width="160" />
              <el-table-column prop="total" :label="t('dashboard.totalRequests')" width="90" />
              <el-table-column prop="blocked" :label="t('dashboard.blocked')" width="90" />
            </el-table>
          </div>
        </el-col>
      </el-row>
    </el-skeleton>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { dashboardApi } from "../api";
import DashboardRecentRecords from "../components/DashboardRecentRecords.vue";
import DashboardWorldIpMap from "../components/DashboardWorldIpMap.vue";

const { t } = useI18n();
const router = useRouter();

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

const goLogs = (decision, extra = {}) => {
  const query = { ...extra };
  if (decision) query.decision = decision;
  router.push({ path: "/logs", query });
};

const onCountryClick = (code) => {
  goLogs(undefined, { country: code });
};

const onCountryRowClick = (row) => {
  goLogs(undefined, { country: row.country_code });
};

const onRiskIpClick = (row) => {
  goLogs("block", { q: row.ip });
};

const onPathClick = (row) => {
  goLogs(undefined, { path: row.path });
};

onMounted(load);
</script>

<style scoped>
.dashboard-page {
  padding: 0;
}

.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.dash-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--ip-text, #0f172a);
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  border-radius: 12px;
  background: var(--ip-bg-card, #fff);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  overflow: hidden;
  border: 1px solid var(--ip-border, transparent);
}

.stat-card::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-total::before {
  background: #3b82f6;
}
.stat-allow::before {
  background: #22c55e;
}
.stat-block::before {
  background: #ef4444;
}
.stat-rate::before {
  background: #f59e0b;
}

.stat-icon {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-icon svg {
  width: 24px;
  height: 24px;
}

.stat-total .stat-icon {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}
.stat-allow .stat-icon {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}
.stat-block .stat-icon {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}
.stat-rate .stat-icon {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  color: var(--ip-text, #0f172a);
}

.stat-label {
  font-size: 13px;
  color: var(--ip-text-secondary, #64748b);
  margin-top: 4px;
}

.map-section {
  margin-bottom: 20px;
}

.section-card {
  background: var(--ip-bg-card, #fff);
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid var(--ip-border, transparent);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--ip-text, #334155);
}

.clickable-table {
  cursor: pointer;
}

.clickable-table :deep(.el-table__row:hover) {
  background: #f0fdf4 !important;
}

@media (max-width: 900px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 500px) {
  .stats-row {
    grid-template-columns: 1fr;
  }
}
</style>
