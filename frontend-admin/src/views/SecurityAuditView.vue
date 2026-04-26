<template>
  <div class="audit-container">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>{{ t('securityAudit.title') }}</span>
        </div>
      </template>

      <div class="filter-bar" style="margin-bottom: 16px; display: flex; gap: 12px; flex-wrap: wrap">
        <el-select
          v-model="filterAction"
          :placeholder="t('securityAudit.filterByAction')"
          clearable
          style="width: 200px"
        >
          <el-option :label="t('securityAudit.allActions')" value="" />
          <el-option
            v-for="(label, key) in actionTypeLabels"
            :key="key"
            :label="label"
            :value="key"
          />
        </el-select>

        <el-date-picker
          v-model="dateRange"
          type="datetimerange"
          range-separator="~"
          :start-placeholder="t('common.startDate')"
          :end-placeholder="t('common.endDate')"
          value-format="YYYY-MM-DD HH:mm:ss"
          style="width: 340px"
        />

        <el-button type="primary" @click="fetchLogs" :loading="loading">
          <el-icon style="margin-right: 4px"><Search /></el-icon>
          {{ t('common.search') }}
        </el-button>
      </div>

      <el-table :data="logs" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="action" :label="t('securityAudit.action')" width="180">
          <template #default="{ row }">
            {{ actionTypeLabels[row.action] || row.action }}
          </template>
        </el-table-column>
        <el-table-column prop="detail" :label="t('securityAudit.detail')" min-width="300" show-overflow-tooltip />
        <el-table-column prop="ip_address" :label="t('securityAudit.ip')" width="140" />
        <el-table-column prop="created_at" :label="t('securityAudit.time')" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 16px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>

      <el-empty v-if="!loading && logs.length === 0" :description="t('securityAudit.noData')" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { Search } from '@element-plus/icons-vue';
import { getSecurityAuditLogsApi } from '@/api';
import { formatDateTime } from '@/utils/time';

const { t } = useI18n();

const logs = ref([]);
const loading = ref(false);
const currentPage = ref(1);
const pageSize = ref(20);
const total = ref(0);
const filterAction = ref('');
const dateRange = ref(null);

const actionTypeLabels = computed(() => ({
  password_change: t('securityAudit.actionTypes.password_change'),
  email_change_request: t('securityAudit.actionTypes.email_change_request'),
  email_change_confirm: t('securityAudit.actionTypes.email_change_confirm'),
  '2fa_enable': t('securityAudit.actionTypes.2fa_enable'),
  '2fa_disable': t('securityAudit.actionTypes.2fa_disable'),
}));

async function fetchLogs() {
  loading.value = true;
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    };
    if (filterAction.value) {
      params.action = filterAction.value;
    }
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_time = dateRange.value[0];
      params.end_time = dateRange.value[1];
    }
    const res = await getSecurityAuditLogsApi(params);
    logs.value = res.data.results || res.data.items || [];
    total.value = res.data.total || logs.value.length;
  } catch (e) {
    console.error('Failed to fetch audit logs:', e);
  } finally {
    loading.value = false;
  }
}

function handleSizeChange(val) {
  pageSize.value = val;
  currentPage.value = 1;
  fetchLogs();
}

function handlePageChange(val) {
  currentPage.value = val;
  fetchLogs();
}

onMounted(() => {
  fetchLogs();
});
</script>

<style scoped>
.audit-container {
  padding: 0;
}
</style>
