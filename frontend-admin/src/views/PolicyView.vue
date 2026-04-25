<template>
  <div class="page-card">
    <h3>{{ t('policy.title') }}</h3>
    <el-form :model="form" label-width="180px">
      <el-form-item :label="t('policy.enabled')"><el-switch v-model="form.enabled" /></el-form-item>
      <el-form-item :label="t('policy.riskThreshold')"><el-input-number v-model="form.risk_score_threshold" :min="0" :max="100" /></el-form-item>
      <el-form-item :label="t('policy.blockedRiskTags')">
        <el-select
          v-model="form.blocked_risk_tags"
          multiple
          filterable
          allow-create
          default-first-option
          :placeholder="t('policy.blockedRiskTagsPlaceholder')"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item :label="t('policy.allowedCountries')">
        <el-select
          v-model="form.allowed_countries"
          multiple
          filterable
          allow-create
          default-first-option
          :placeholder="t('policy.allowedCountriesPlaceholder')"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item :label="t('policy.blockedCountries')">
        <el-select
          v-model="form.blocked_countries"
          multiple
          filterable
          allow-create
          default-first-option
          :placeholder="t('policy.blockedCountriesPlaceholder')"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item :label="t('policy.ipWhitelist')">
        <el-select
          v-model="form.ip_whitelist"
          multiple
          filterable
          allow-create
          default-first-option
          :placeholder="t('policy.ipWhitelistPlaceholder')"
          style="width: 100%"
        />
        <span class="hint">{{ t('policy.ipWhitelistHint') }}</span>
      </el-form-item>
      <el-form-item :label="t('policy.ipBlacklist')">
        <el-select
          v-model="form.ip_blacklist"
          multiple
          filterable
          allow-create
          default-first-option
          :placeholder="t('policy.ipBlacklistPlaceholder')"
          style="width: 100%"
        />
        <span class="hint">{{ t('policy.ipBlacklistHint') }}</span>
      </el-form-item>
      <el-divider content-position="left">{{ t('policy.geoPoolDivider') }}</el-divider>
      <p class="hint block-hint">
        {{ t('policy.geoPoolHint') }}<code>0 3 * * * python manage.py sync_geo_ip_pools</code>
      </p>
      <el-form-item :label="t('policy.chinaPoolRule')">
        <el-select v-model="form.china_pool_rule" style="width: 100%">
          <el-option :label="t('policy.poolRuleOff')" value="off" />
          <el-option :label="t('policy.poolRuleAllowOnly')" value="allow_only_in_pool" />
          <el-option :label="t('policy.poolRuleBlock')" value="block_in_pool" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('policy.internationalPoolRule')">
        <el-select v-model="form.international_pool_rule" style="width: 100%">
          <el-option :label="t('policy.poolRuleOff')" value="off" />
          <el-option :label="t('policy.poolRuleAllowOnlyShort')" value="allow_only_in_pool" />
          <el-option :label="t('policy.poolRuleBlock')" value="block_in_pool" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('policy.feedUrlLabel')">
        <div class="feed-readonly">
          <div><strong>{{ t('policy.feedUrlChina') }}</strong>：{{ form.pool_feed_urls?.geo_china_pool_url || "—" }}</div>
          <div><strong>{{ t('policy.feedUrlInternational') }}</strong>：{{ form.pool_feed_urls?.geo_international_pool_url || t('policy.feedUrlNotConfigured') }}</div>
        </div>
      </el-form-item>
      <el-form-item :label="t('policy.poolSyncStatus')">
        <el-table :data="poolMeta.pools" size="small" border :empty-text="t('policy.noSyncRecord')">
          <el-table-column prop="pool_key" :label="t('policy.pool')" width="120" />
          <el-table-column prop="line_count" :label="t('policy.lineCount')" width="80" />
          <el-table-column prop="v4_interval_count" :label="t('policy.ipv4Interval')" width="100" />
          <el-table-column prop="last_ok_at" :label="t('policy.lastSuccess')" min-width="160" />
          <el-table-column prop="last_error" :label="t('policy.error')" min-width="200" show-overflow-tooltip />
        </el-table>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="syncing" :disabled="!canEditPolicy" @click="onSyncPools">
          {{ t('policy.syncNow') }}
        </el-button>
      </el-form-item>
      <el-form-item :label="t('policy.rateLimit')">
        <el-input-number v-model="form.rate_limit_per_minute" :min="0" :max="100000" />
        <span class="hint">{{ t('policy.rateLimitHint') }}</span>
      </el-form-item>
      <el-form-item :label="t('policy.failOpen')"><el-switch v-model="form.fail_open" /></el-form-item>
      <el-form-item :label="t('policy.failOpenPathPrefixes')">
        <el-select
          v-model="form.fail_open_path_prefixes"
          multiple
          filterable
          allow-create
          default-first-option
          :placeholder="t('policy.failOpenPathPrefixesPlaceholder')"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item :label="t('policy.failClosePathPrefixes')">
        <el-select
          v-model="form.fail_close_path_prefixes"
          multiple
          filterable
          allow-create
          default-first-option
          :placeholder="t('policy.failClosePathPrefixesPlaceholder')"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item :label="t('policy.blockStatusCode')"><el-input-number v-model="form.block_status_code" :min="400" :max="499" /></el-form-item>
      <el-form-item :label="t('policy.cacheTtl')"><el-input-number v-model="form.cache_ttl" :min="60" /></el-form-item>
      <el-form-item :label="t('policy.banTtl')"><el-input-number v-model="form.ban_ttl" :min="60" /></el-form-item>
      <el-form-item :label="t('policy.useDbLog')">
        <el-switch v-model="form.use_db_log" />
        <span class="hint">{{ t('policy.useDbLogHint') }}</span>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="saving" :disabled="!canEditPolicy" @click="onSave">{{ t('policy.savePolicy') }}</el-button>
        <el-button @click="reload">{{ t('policy.reload') }}</el-button>
        <span v-if="!canEditPolicy" class="hint">{{ t('policy.viewOnlyHint') }}</span>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import { getGeoPoolsStatusApi, getPolicyApi, syncGeoPoolsApi, updatePolicyApi } from "../api";
import { useAuthStore } from "../stores/auth";

const { t } = useI18n();

const emptyForm = () => ({
  enabled: true,
  risk_score_threshold: 70,
  blocked_risk_tags: [],
  allowed_countries: [],
  blocked_countries: [],
  ip_whitelist: [],
  ip_blacklist: [],
  rate_limit_per_minute: 0,
  fail_open: true,
  fail_open_path_prefixes: [],
  fail_close_path_prefixes: [],
  block_status_code: 403,
  cache_ttl: 3600,
  ban_ttl: 86400,
  use_db_log: false,
  china_pool_rule: "off",
  international_pool_rule: "off",
  pool_feed_urls: { geo_china_pool_url: "", geo_international_pool_url: "" },
});

const form = reactive(emptyForm());
const poolMeta = reactive({ pools: [] });
const saving = ref(false);
const syncing = ref(false);
const authStore = useAuthStore();
const canEditPolicy = computed(() => authStore.hasPerm("django_ip_safeguard.change_ipguardpolicy"));

const loadPoolStatus = async () => {
  try {
    const data = await getGeoPoolsStatusApi();
    poolMeta.pools = data.pools || [];
  } catch {
    poolMeta.pools = [];
  }
};

const reload = async () => {
  Object.assign(form, emptyForm(), await getPolicyApi());
  await loadPoolStatus();
};

const onSyncPools = async () => {
  if (!canEditPolicy.value) {
    ElMessage.warning(t('policy.needChangePerm'));
    return;
  }
  syncing.value = true;
  try {
    await syncGeoPoolsApi();
    ElMessage.success(t('common.success'));
    await loadPoolStatus();
  } finally {
    syncing.value = false;
  }
};

onMounted(reload);

const onSave = async () => {
  saving.value = true;
  try {
    if (!canEditPolicy.value) {
      ElMessage.warning(t('policy.noChangePerm'));
      return;
    }
    await updatePolicyApi({ ...form });
    ElMessage.success(t('common.success'));
    await reload();
  } finally {
    saving.value = false;
  }
};
</script>

<style scoped>
.hint {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}
.block-hint {
  margin: 0 0 12px;
  margin-left: 0;
  line-height: 1.5;
}
.feed-readonly {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  word-break: break-all;
}
.sync-btn {
  margin-top: 10px;
}
</style>
