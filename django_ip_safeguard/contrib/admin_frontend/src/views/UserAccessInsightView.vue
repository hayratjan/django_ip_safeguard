<template>
  <div class="page-card">
    <h3>{{ t("userAccessInsight.title") }}</h3>
    <p class="intro">{{ t("userAccessInsight.intro") }}</p>

    <el-space wrap style="margin-bottom: 16px">
      <el-input
        v-model="userIdInput"
        :placeholder="t('userAccessInsight.userId')"
        style="width: 160px"
        clearable
        @keyup.enter="load"
      />
      <el-input-number v-model="days" :min="1" :max="180" :step="1" controls-position="right" />
      <span class="hint">{{ t("userAccessInsight.days") }}</span>
      <el-button type="primary" :loading="loading" @click="load">{{ t("userAccessInsight.load") }}</el-button>
    </el-space>

    <template v-if="summary">
      <el-descriptions :column="3" border size="small" style="margin-bottom: 16px">
        <el-descriptions-item :label="t('userAccessInsight.userLabel')">
          {{ summary.user.username || "—" }}
          <el-tag v-if="summary.user.deleted" type="info" size="small" style="margin-left: 8px">
            {{ t("userAccessInsight.deletedUser") }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label="t('userAccessInsight.visitTotal')">
          {{ summary.visit_total }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('userAccessInsight.distinctIp')">
          {{ summary.distinct_ip_count }}
        </el-descriptions-item>
      </el-descriptions>

      <el-table :data="summary.by_ip" size="small" max-height="520" stripe>
        <el-table-column prop="ip" :label="t('userAccessInsight.colIp')" width="150" />
        <el-table-column prop="request_count" :label="t('userAccessInsight.colCount')" width="90" />
        <el-table-column prop="last_at" :label="t('userAccessInsight.colLast')" width="190" />
        <el-table-column prop="country_code" :label="t('logs.country')" width="80" />
        <el-table-column prop="country_name" :label="t('logs.countryName')" min-width="120" show-overflow-tooltip />
        <el-table-column prop="region" :label="t('userAccessInsight.colRegion')" min-width="100" show-overflow-tooltip />
        <el-table-column prop="city" :label="t('userAccessInsight.colCity')" min-width="100" show-overflow-tooltip />
      </el-table>
      <p v-if="summary.by_ip?.length >= 200" class="table-footnote">{{ t("userAccessInsight.topIpHint") }}</p>
    </template>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import { accessLogUserSummaryApi } from "../api";

const { t } = useI18n();

const userIdInput = ref("");
const days = ref(30);
const loading = ref(false);
const summary = ref(null);

const load = async () => {
  const raw = String(userIdInput.value || "").trim();
  const uid = parseInt(raw, 10);
  if (!raw || Number.isNaN(uid) || uid <= 0) {
    ElMessage.warning(t("userAccessInsight.needUserId"));
    return;
  }
  loading.value = true;
  summary.value = null;
  try {
    summary.value = await accessLogUserSummaryApi({ user_id: uid, days: days.value });
  } catch {
    ElMessage.error(t("userAccessInsight.loadFail"));
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.intro {
  color: var(--ip-text-secondary, #606266);
  font-size: 13px;
  margin: 0 0 12px;
  line-height: 1.5;
}
.hint {
  font-size: 13px;
  color: var(--ip-text-secondary, #606266);
}
.table-footnote {
  margin-top: 8px;
  font-size: 12px;
  color: var(--ip-text-secondary, #606266);
}
</style>
