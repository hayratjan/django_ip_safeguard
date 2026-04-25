<template>
  <div class="page-card">
    <h3>审计日志</h3>
    <el-space wrap style="margin-bottom: 12px">
      <el-select v-model="query.decision" placeholder="决策" style="width: 120px" clearable>
        <el-option label="全部" value="" />
        <el-option label="放行" value="allow" />
        <el-option label="拦截" value="block" />
      </el-select>
      <el-input v-model="query.country" placeholder="国家码" style="width: 100px" clearable />
      <el-input v-model="query.path" placeholder="路径包含" style="width: 180px" clearable />
      <el-input v-model="query.q" placeholder="搜索 IP" style="width: 200px" clearable />
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        value-format="YYYY-MM-DD"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        style="width: 260px"
      />
      <el-button @click="onSearch">查询</el-button>
      <el-button :loading="exporting" @click="onExport">导出 CSV</el-button>
    </el-space>

    <el-table v-loading="loading" :data="items" size="small">
      <el-table-column prop="ip" label="IP" width="150" />
      <el-table-column prop="country_code" label="国家" width="90" />
      <el-table-column prop="risk_score" label="风险分" width="90" />
      <el-table-column prop="decision" label="决策" width="90" />
      <el-table-column prop="reason" label="原因" show-overflow-tooltip />
      <el-table-column prop="path" label="路径" width="200" show-overflow-tooltip />
      <el-table-column prop="created_at" label="时间" width="190" />
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
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { getAccessLogsApi } from "../api";
import { downloadAccessLogsCsv } from "../api/export";

const query = reactive({ q: "", country: "", decision: "", path: "" });
const dateRange = ref(null);
const items = ref([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const loading = ref(false);
const exporting = ref(false);

// 列表分页与导出共用筛选字段（导出不带 page，最多后端 1 万条）
const filterParams = () => {
  const p = {
    q: query.q || undefined,
    country: query.country || undefined,
    decision: query.decision || undefined,
    path: query.path || undefined,
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

const onExport = async () => {
  exporting.value = true;
  try {
    await downloadAccessLogsCsv(filterParams());
    ElMessage.success("已开始下载");
  } catch (e) {
    ElMessage.error("导出失败，请检查登录态或网络");
  } finally {
    exporting.value = false;
  }
};

onMounted(load);
</script>
