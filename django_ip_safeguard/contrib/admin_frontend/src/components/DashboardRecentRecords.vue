<template>
  <div class="recent-wrap">
    <div class="recent-toolbar">
      <span class="toolbar-label">统计范围</span>
      <el-radio-group v-model="days" size="small">
        <el-radio-button :label="3">近 3 天</el-radio-button>
        <el-radio-button :label="7">近 7 天</el-radio-button>
        <el-radio-button :label="14">近 14 天</el-radio-button>
        <el-radio-button :label="30">近 30 天</el-radio-button>
      </el-radio-group>
      <el-button size="small" :loading="loading" @click="load">刷新</el-button>
    </div>

    <el-row v-if="summary" :gutter="12" class="summary-row">
      <el-col :span="6">
        <div class="mini-stat" @click="goLogs()">
          <span class="mini-value">{{ summary.total_access || 0 }}</span>
          <span class="mini-label">访问总次数</span>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat mini-block" @click="goLogs('block')">
          <span class="mini-value">{{ summary.total_blocks || 0 }}</span>
          <span class="mini-label">拦截（攻击）次数</span>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat mini-allow" @click="goLogs('allow')">
          <span class="mini-value">{{ summary.total_allows || 0 }}</span>
          <span class="mini-label">放行次数</span>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat mini-ban" @click="goLogs()">
          <span class="mini-value">{{ summary.total_ban_events || 0 }}</span>
          <span class="mini-label">封禁事件数</span>
        </div>
      </el-col>
    </el-row>

    <h4 class="sub">按日汇总（放行 / 拦截）</h4>
    <el-table v-loading="loading" :data="dailyBreakdown" size="small" max-height="220" style="margin-bottom: 16px">
      <el-table-column prop="date" label="日期" width="120" />
      <el-table-column prop="allow" label="放行" width="100" />
      <el-table-column prop="block" label="拦截" width="100" />
      <el-table-column prop="total" label="合计" width="100" />
    </el-table>

    <el-row :gutter="12">
      <el-col :xs="24" :lg="12">
        <h4 class="sub">攻击 / 拦截记录（最新）</h4>
        <p class="hint">decision=block 的审计记录，反映策略命中与风险拦截。</p>
        <el-table v-loading="loading" :data="recentAttacks" size="small" max-height="320" class="clickable-table" @row-click="onAttackRowClick">
          <el-table-column prop="created_at" label="时间" width="168" />
          <el-table-column prop="ip" label="IP" width="130" />
          <el-table-column prop="country_code" label="国家" width="72" />
          <el-table-column prop="risk_score" label="风险分" width="72" />
          <el-table-column prop="reason" label="原因" min-width="100" show-overflow-tooltip />
          <el-table-column prop="path" label="路径" width="120" show-overflow-tooltip />
        </el-table>
      </el-col>
      <el-col :xs="24" :lg="12">
        <h4 class="sub">IP 访问记录（最新）</h4>
        <p class="hint">含放行与拦截的最近访问样本，完整检索请用「审计日志」页。</p>
        <el-table v-loading="loading" :data="recentAccess" size="small" max-height="320" class="clickable-table" @row-click="onAccessRowClick">
          <el-table-column prop="created_at" label="时间" width="168" />
          <el-table-column prop="ip" label="IP" width="130" />
          <el-table-column prop="decision" label="决策" width="72">
            <template #default="{ row }">
              <el-tag :type="row.decision === 'block' ? 'danger' : 'success'" size="small" effect="plain">
                {{ row.decision === 'block' ? '拦截' : '放行' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="country_code" label="国家" width="72" />
          <el-table-column prop="risk_score" label="风险分" width="72" />
          <el-table-column prop="path" label="路径" min-width="100" show-overflow-tooltip />
        </el-table>
      </el-col>
    </el-row>

    <h4 class="sub" style="margin-top: 20px">近期封禁事件</h4>
    <el-table v-loading="loading" :data="recentBans" size="small" max-height="200" class="clickable-table" @row-click="onBanRowClick">
      <el-table-column prop="created_at" label="时间" width="168" />
      <el-table-column prop="ip" label="IP" width="130" />
      <el-table-column prop="ban_source" label="来源" width="90" />
      <el-table-column prop="ban_reason" label="原因" show-overflow-tooltip />
      <el-table-column prop="is_active" label="生效" width="72">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'danger' : 'info'" size="small" effect="plain">
            {{ row.is_active ? "是" : "否" }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import { useRouter } from "vue-router";
import { recentRecordsApi } from "../api";

const router = useRouter();

const days = ref(7);
const loading = ref(false);
const summary = ref(null);
const dailyBreakdown = ref([]);
const recentAttacks = ref([]);
const recentAccess = ref([]);
const recentBans = ref([]);

const load = async () => {
  loading.value = true;
  try {
    const data = await recentRecordsApi({ days: days.value });
    summary.value = data.summary || null;
    dailyBreakdown.value = data.daily_breakdown || [];
    recentAttacks.value = data.recent_attacks || [];
    recentAccess.value = data.recent_access || [];
    recentBans.value = data.recent_bans || [];
  } finally {
    loading.value = false;
  }
};

const goLogs = (decision, extra = {}) => {
  const query = { ...extra };
  if (decision) query.decision = decision;
  router.push({ path: "/logs", query });
};

const onAttackRowClick = (row) => {
  goLogs("block", { q: row.ip });
};

const onAccessRowClick = (row) => {
  goLogs(row.decision, { q: row.ip });
};

const onBanRowClick = (row) => {
  goLogs("block", { q: row.ip });
};

watch(days, () => load());
load();
</script>

<style scoped>
.recent-wrap {
  width: 100%;
}

.recent-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.toolbar-label {
  font-size: 13px;
  color: var(--ip-text-secondary, #606266);
}

.summary-row {
  margin-bottom: 16px;
}

.mini-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  border-radius: 8px;
  background: var(--ip-bg-card-hover, #f8fafc);
  cursor: pointer;
  transition: background 0.2s;
  border: 1px solid var(--ip-border, transparent);
}

.mini-stat:hover {
  background: var(--ip-border, #e2e8f0);
}

.mini-block {
  background: rgba(239, 68, 68, 0.08);
}
.mini-block:hover {
  background: rgba(239, 68, 68, 0.15);
}

.mini-allow {
  background: rgba(34, 197, 94, 0.08);
}
.mini-allow:hover {
  background: rgba(34, 197, 94, 0.15);
}

.mini-ban {
  background: rgba(245, 158, 11, 0.08);
}
.mini-ban:hover {
  background: rgba(245, 158, 11, 0.15);
}

.mini-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--ip-text, #0f172a);
}

.mini-label {
  font-size: 12px;
  color: var(--ip-text-secondary, #64748b);
  margin-top: 2px;
}

.sub {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ip-text-secondary, #606266);
}

.hint {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--ip-text-secondary, #909399);
  line-height: 1.5;
}

.clickable-table {
  cursor: pointer;
}

.clickable-table :deep(.el-table__row:hover) {
  background: #f0fdf4 !important;
}
</style>
