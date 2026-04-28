<template>
  <div class="page-card">
    <h3>{{ t("logs.title") }}</h3>
    <el-space wrap style="margin-bottom: 12px">
      <el-select v-model="query.decision" :placeholder="t('logs.decisionFilter')" style="width: 120px" clearable>
        <el-option :label="t('logs.all')" value="" />
        <el-option :label="t('logs.allow')" value="allow" />
        <el-option :label="t('logs.block')" value="block" />
      </el-select>
      <el-input v-model="query.country" :placeholder="t('logs.countryCode')" style="width: 100px" clearable />
      <el-input v-model="query.username" :placeholder="t('logs.username')" style="width: 120px" clearable />
      <el-input v-model="query.user_id" :placeholder="t('logs.userId')" style="width: 110px" clearable />
      <el-input v-model="query.path" :placeholder="t('logs.pathContains')" style="width: 160px" clearable />
      <el-input v-model="query.q" :placeholder="t('logs.searchIp')" style="width: 160px" clearable />
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        value-format="YYYY-MM-DD"
        :range-separator="t('logs.to')"
        :start-placeholder="t('logs.startDate')"
        :end-placeholder="t('logs.endDate')"
        style="width: 260px"
      />
      <el-button type="primary" @click="onSearch">{{ t("logs.query") }}</el-button>
      <el-button :loading="exporting" @click="onExport">{{ t("logs.exportCsv") }}</el-button>
    </el-space>

    <el-table v-loading="loading" :data="items" size="small" table-layout="auto">
      <el-table-column prop="created_at" :label="t('logs.time')" width="178" />
      <el-table-column :label="t('logs.user')" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.username">{{ row.username }}</span>
          <span v-else-if="row.user_id">#{{ row.user_id }}</span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column prop="method" :label="t('logs.method')" width="72" />
      <el-table-column prop="ip" :label="t('logs.ip')" width="138" />
      <el-table-column prop="country_code" :label="t('logs.country')" width="72" />
      <el-table-column prop="country_name" :label="t('logs.countryName')" min-width="100" show-overflow-tooltip />
      <el-table-column prop="region" :label="t('logs.region')" min-width="90" show-overflow-tooltip />
      <el-table-column prop="city" :label="t('logs.city')" min-width="90" show-overflow-tooltip />
      <el-table-column prop="path" :label="t('logs.path')" min-width="160" show-overflow-tooltip />
      <el-table-column prop="risk_score" :label="t('logs.riskScore')" width="80" />
      <el-table-column prop="decision" :label="t('logs.decision')" width="100">
        <template #default="{ row }">
          <el-tag :type="decisionTagType(row.decision)" size="small" effect="plain">
            {{ decisionLabel(row.decision) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="reason" :label="t('logs.reason')" min-width="140" show-overflow-tooltip />
    </el-table>
    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      style="margin-top: 12px; justify-content: flex-end"
      layout="total, sizes, prev, pager, next"
      :total="total"
      :page-sizes="[10, 20, 50, 100]"
      @current-change="load"
      @size-change="onSizeChange"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import { getAccessLogsApi } from "../api";
import { downloadAccessLogsCsv } from "../api/export";

const route = useRoute();
const { t } = useI18n();

const query = reactive({ q: "", country: "", decision: "", path: "", username: "", user_id: "" });
const dateRange = ref(null);
const items = ref([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const loading = ref(false);
const exporting = ref(false);

const filterParams = () => {
  const p = {
    q: query.q || undefined,
    country: query.country || undefined,
    decision: query.decision || undefined,
    path: query.path || undefined,
    username: query.username || undefined,
    user_id: query.user_id || undefined,
  };
  if (dateRange.value?.length === 2) {
    p.start = dateRange.value[0];
    p.end = dateRange.value[1];
  }
  return p;
};

const listParams = () => ({
  page: page.value,
  page_size: pageSize.value,
  ...filterParams(),
});

const load = async () => {
  loading.value = true;
  try {
    const data = await getAccessLogsApi(listParams());
    items.value = data.items || [];
    total.value = data.pagination?.total ?? 0;
  } finally {
    loading.value = false;
  }
};

const onSearch = () => {
  page.value = 1;
  load();
};

const onSizeChange = () => {
  page.value = 1;
  load();
};

/** 决策列展示：含 security_audit 等非 allow/block */
const decisionTagType = (d) => {
  if (d === "block") return "danger";
  if (d === "allow") return "success";
  return "info";
};

const decisionLabel = (d) => {
  if (d === "block") return t("logs.block");
  if (d === "allow") return t("logs.allow");
  return d || "—";
};

const onExport = async () => {
  exporting.value = true;
  try {
    await downloadAccessLogsCsv(filterParams());
    ElMessage.success(t("logs.exportSuccess"));
  } catch {
    ElMessage.error(t("logs.exportFailed"));
  } finally {
    exporting.value = false;
  }
};

const applyRouteQuery = (q) => {
  if (q.q) query.q = q.q;
  if (q.country) query.country = q.country;
  if (q.decision) query.decision = q.decision;
  if (q.path) query.path = q.path;
  if (q.username) query.username = q.username;
  if (q.user_id) query.user_id = q.user_id;
};

watch(
  () => route.query,
  (q) => {
    applyRouteQuery(q);
    load();
  },
  { immediate: true }
);

onMounted(() => {
  applyRouteQuery(route.query);
});
</script>
