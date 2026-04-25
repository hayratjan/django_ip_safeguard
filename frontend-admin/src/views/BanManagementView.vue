<template>
  <div class="page-card">
    <h3>封禁管理</h3>
    <el-space wrap style="margin-bottom: 12px">
      <el-input v-model="query.q" placeholder="搜索 IP" style="width: 220px" clearable />
      <el-select v-model="query.active" placeholder="状态" style="width: 120px" clearable>
        <el-option label="全部" value="" />
        <el-option label="生效" value="true" />
        <el-option label="失效" value="false" />
      </el-select>
      <el-input v-model="query.source" placeholder="来源 manual/rule…" style="width: 160px" clearable />
      <el-button @click="onSearch">查询</el-button>
    </el-space>

    <el-space wrap style="margin-bottom: 12px">
      <el-input v-model="banForm.ip" placeholder="IP 地址" style="width: 220px" />
      <el-input v-model="banForm.reason" placeholder="原因" style="width: 240px" />
      <el-input-number v-model="banForm.ttl" :min="60" />
      <el-button type="danger" :loading="banning" @click="onBan">手动封禁</el-button>
    </el-space>

    <el-table v-loading="loading" :data="items" size="small">
      <el-table-column prop="ip" label="IP" width="160" />
      <el-table-column prop="ban_reason" label="原因" show-overflow-tooltip />
      <el-table-column prop="ban_source" label="来源" width="90" />
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">{{ row.is_active ? "生效" : "失效" }}</template>
      </el-table-column>
      <el-table-column prop="expired_at" label="过期时间" width="200" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="!row.is_active" @click="onUnban(row.ip)">解封</el-button>
        </template>
      </el-table-column>
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
import { banIpApi, getBanListApi, unbanIpApi } from "../api";

const query = reactive({ q: "", active: "", source: "" });
const banForm = reactive({ ip: "", reason: "manual_ban", ttl: 86400 });
const items = ref([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const loading = ref(false);
const banning = ref(false);

const load = async () => {
  loading.value = true;
  try {
    const data = await getBanListApi({
      page: page.value,
      page_size: pageSize.value,
      q: query.q || undefined,
      active: query.active || undefined,
      source: query.source || undefined,
    });
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

const onBan = async () => {
  banning.value = true;
  try {
    await banIpApi(banForm);
    ElMessage.success("封禁成功");
    await load();
  } finally {
    banning.value = false;
  }
};

const onUnban = async (ip) => {
  await unbanIpApi({ ip });
  ElMessage.success("解封成功");
  await load();
};

onMounted(load);
</script>
