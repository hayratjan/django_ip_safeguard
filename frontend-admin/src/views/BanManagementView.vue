<template>
  <div class="page-card">
    <h3>{{ t('ban.title') }}</h3>
    <el-space wrap style="margin-bottom: 12px">
      <el-input v-model="query.q" :placeholder="t('ban.searchIp')" style="width: 220px" clearable />
      <el-select v-model="query.active" :placeholder="t('ban.statusFilter')" style="width: 120px" clearable>
        <el-option :label="t('common.all')" value="" />
        <el-option :label="t('ban.activeStatus')" value="true" />
        <el-option :label="t('ban.inactiveStatus')" value="false" />
      </el-select>
      <el-input v-model="query.source" :placeholder="t('ban.sourceFilter')" style="width: 160px" clearable />
      <el-button @click="onSearch">{{ t('common.query') }}</el-button>
    </el-space>

    <el-space wrap style="margin-bottom: 12px">
      <el-input v-model="banForm.ip" :placeholder="t('ban.ip')" style="width: 220px" />
      <el-input v-model="banForm.reason" :placeholder="t('ban.reason')" style="width: 240px" />
      <el-input-number v-model="banForm.ttl" :min="60" />
      <el-button type="danger" :loading="banning" @click="onBan">{{ t('ban.manualBan') }}</el-button>
    </el-space>

    <el-table v-loading="loading" :data="items" size="small">
      <el-table-column prop="ip" label="IP" width="160" />
      <el-table-column prop="ban_reason" :label="t('ban.banReason')" show-overflow-tooltip />
      <el-table-column prop="ban_source" :label="t('ban.banSource')" width="90" />
      <el-table-column prop="is_active" :label="t('common.status')" width="80">
        <template #default="{ row }">{{ row.is_active ? t('common.active') : t('common.inactive') }}</template>
      </el-table-column>
      <el-table-column prop="expired_at" :label="t('ban.expiredAt')" width="200" />
      <el-table-column :label="t('common.actions')" width="100">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="!row.is_active" @click="onUnban(row.ip)">{{ t('ban.unban') }}</el-button>
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
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import { banIpApi, getBanListApi, unbanIpApi } from "../api";

const { t } = useI18n();

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
    ElMessage.success(t('ban.banSuccess'));
    await load();
  } finally {
    banning.value = false;
  }
};

const onUnban = async (ip) => {
  await unbanIpApi({ ip });
  ElMessage.success(t('ban.unbanSuccess'));
  await load();
};

onMounted(load);
</script>
