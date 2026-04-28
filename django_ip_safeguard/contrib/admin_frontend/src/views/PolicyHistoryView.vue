<template>
  <div class="page-card">
    <h3>{{ t('policyHistory.title') }}</h3>
    <p class="hint">{{ t('policyHistory.hint') }}</p>
    <el-form inline class="filter-row">
      <el-form-item :label="t('policyHistory.filterPolicy')">
        <el-input v-model="filterPolicy" clearable style="width: 200px" @keyup.enter="load" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="load">{{ t('common.refresh') }}</el-button>
      </el-form-item>
    </el-form>
    <el-table :data="items" v-loading="loading" border size="small">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="policy_name" :label="t('policyHistory.policy')" width="140" />
      <el-table-column prop="created_at" :label="t('policyHistory.time')" min-width="180" />
      <el-table-column prop="actor" :label="t('policyHistory.actor')" width="120" />
      <el-table-column :label="t('policyHistory.actions')" width="120" fixed="right">
        <template #default="{ row }">
          <el-button
            type="danger"
            link
            size="small"
            :disabled="!canRollback"
            @click="onRollback(row)"
          >
            {{ t('policyHistory.rollback') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="load"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { ElMessage, ElMessageBox } from "element-plus";
import { listPolicySnapshotsApi, rollbackPolicySnapshotApi } from "../api";
import { useAuthStore } from "../stores/auth";

const { t } = useI18n();
const authStore = useAuthStore();
const canRollback = computed(() => authStore.hasPerm("django_ip_safeguard.change_ipguardpolicy"));

const loading = ref(false);
const items = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const filterPolicy = ref("");

const load = async () => {
  loading.value = true;
  try {
    const data = await listPolicySnapshotsApi({
      policy: filterPolicy.value || undefined,
      page: page.value,
      page_size: pageSize,
    });
    items.value = data.items || [];
    total.value = data.total || 0;
  } catch {
    items.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
};

const onRollback = async (row) => {
  if (!canRollback.value) return;
  try {
    await ElMessageBox.confirm(t("policyHistory.confirmRollback"), t("common.warning"), {
      type: "warning",
    });
    await rollbackPolicySnapshotApi(row.id);
    ElMessage.success(t("common.success"));
    await load();
  } catch (e) {
    if (e !== "cancel") ElMessage.error(String(e?.response?.data?.message || e));
  }
};

onMounted(load);
</script>

<style scoped>
.hint {
  color: #909399;
  font-size: 13px;
  margin-bottom: 12px;
}
.filter-row {
  margin-bottom: 12px;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
