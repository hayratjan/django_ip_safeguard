<template>
  <div class="page-card">
    <div class="policy-head">
      <h3>{{ t('policy.title') }}</h3>
      <router-link v-if="canViewPolicy" class="history-link" to="/policy-history">{{ t('nav.policyHistory') }}</router-link>
    </div>

    <div class="policy-list-wrap">
      <el-table
        :data="policies"
        size="small"
        border
        highlight-current-row
        max-height="240"
        :empty-text="t('policy.noPolicies')"
        @row-click="onSelectPolicy"
      >
        <el-table-column prop="name" :label="t('policy.colName')" min-width="120" />
        <el-table-column prop="priority" :label="t('policy.colPriority')" width="90" />
        <el-table-column prop="enabled" :label="t('policy.colEnabled')" width="80">
          <template #default="{ row }">{{ row.enabled ? '✓' : '—' }}</template>
        </el-table-column>
        <el-table-column prop="medium_action" :label="t('policy.colMedium')" width="100" />
        <el-table-column prop="high_action" :label="t('policy.colHigh')" width="100" />
      </el-table>
      <div class="policy-toolbar">
        <el-button size="small" :loading="loadingList" @click="loadPoliciesList">{{ t('policy.refreshPolicies') }}</el-button>
        <el-button v-if="canEditPolicy" size="small" type="primary" @click="showCreate = true">{{ t('policy.newPolicy') }}</el-button>
        <span class="hint">{{ t('policy.editingLabel') }} <code>{{ currentPolicyName }}</code></span>
      </div>
    </div>

    <el-dialog v-model="showCreate" :title="t('policy.newPolicy')" width="420px" @closed="newPolicyName = ''">
      <el-input v-model="newPolicyName" :placeholder="t('policy.newPolicyPlaceholder')" maxlength="64" show-word-limit />
      <template #footer>
        <el-button @click="showCreate = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="creating" @click="onCreatePolicy">{{ t('common.confirm') }}</el-button>
      </template>
    </el-dialog>

    <el-form :model="form" label-width="180px">
      <el-divider content-position="left">{{ t('policy.v2Divider') }}</el-divider>
      <el-form-item :label="t('policy.priority')"><el-input-number v-model="form.priority" :min="1" :max="999999" /></el-form-item>
      <el-form-item :label="t('policy.matchHost')">
        <el-input v-model="form.match_host_regex" :placeholder="t('policy.matchHostPh')" clearable />
      </el-form-item>
      <el-form-item :label="t('policy.matchPaths')">
        <el-select v-model="form.match_path_prefixes" multiple filterable allow-create style="width: 100%" />
      </el-form-item>
      <el-form-item :label="t('policy.matchMethods')">
        <el-select v-model="form.match_methods" multiple filterable allow-create style="width: 100%" />
      </el-form-item>
      <el-form-item :label="t('policy.mediumAction')">
        <el-select v-model="form.medium_action" style="width: 100%">
          <el-option v-for="a in actionChoices" :key="a" :label="a" :value="a" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('policy.highAction')">
        <el-select v-model="form.high_action" style="width: 100%">
          <el-option v-for="a in actionChoices" :key="a" :label="a" :value="a" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('policy.tierJson')">
        <el-input v-model="tierJson" type="textarea" :rows="2" :placeholder="t('policy.tierJsonPh')" />
      </el-form-item>
      <el-form-item :label="t('policy.weightsJson')">
        <el-input v-model="weightsJson" type="textarea" :rows="2" :placeholder="t('policy.weightsJsonPh')" />
      </el-form-item>

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

      <el-divider content-position="left">{{ t("policy.countrySection") }}</el-divider>
      <p class="hint block-hint">{{ t("policy.countrySectionHint") }}</p>
      <el-form-item :label="t('policy.countryMode')">
        <el-radio-group v-model="form.country_mode">
          <el-radio-button label="default">{{ t("policy.countryModeDefault") }}</el-radio-button>
          <el-radio-button label="allowlist">{{ t("policy.countryModeAllowlist") }}</el-radio-button>
          <el-radio-button label="blacklist">{{ t("policy.countryModeBlacklist") }}</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="form.country_mode === 'allowlist'" :label="t('policy.blockUnknownCountry')">
        <el-switch v-model="form.block_unknown_country" />
        <span class="hint">{{ t("policy.blockUnknownHint") }}</span>
      </el-form-item>

      <el-form-item :label="t('policy.allowedCountries')">
        <div class="country-toolbar">
          <el-button size="small" @click="mergeCommonAllowed">{{ t("policy.mergeCommonCountries") }}</el-button>
          <el-button size="small" @click="clearAllowed">{{ t("policy.clearAllowed") }}</el-button>
          <el-button size="small" @click="clearBlocked">{{ t("policy.clearBlocked") }}</el-button>
        </div>
        <el-select
          v-model="form.allowed_countries"
          multiple
          filterable
          collapse-tags
          collapse-tags-tooltip
          :placeholder="t('policy.allowedCountriesPlaceholder')"
          style="width: 100%"
        >
          <el-option v-for="opt in countryOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('policy.blockedCountries')">
        <el-select
          v-model="form.blocked_countries"
          multiple
          filterable
          collapse-tags
          collapse-tags-tooltip
          :placeholder="t('policy.blockedCountriesPlaceholder')"
          style="width: 100%"
        >
          <el-option v-for="opt in countryOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
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
import {
  createPolicyApi,
  getGeoPoolsStatusApi,
  getPolicyByNameApi,
  listPoliciesApi,
  syncGeoPoolsApi,
  updatePolicyByNameApi,
} from "../api";
import { COMMON_ISO2, COUNTRY_ISO2_OPTIONS } from "../constants/policyGeo";
import { useAuthStore } from "../stores/auth";

const { t, locale } = useI18n();

const actionChoices = ["allow", "log_only", "rate_limit", "challenge", "block", "ban"];

const emptyForm = () => ({
  name: "default",
  priority: 10000,
  match_host_regex: "",
  match_path_prefixes: [],
  match_methods: [],
  tier_thresholds: {},
  signal_weights: {},
  medium_action: "block",
  high_action: "ban",
  enabled: true,
  risk_score_threshold: 70,
  blocked_risk_tags: [],
  country_mode: "default",
  block_unknown_country: true,
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
const tierJson = ref("{}");
const weightsJson = ref("{}");
const poolMeta = reactive({ pools: [] });
const saving = ref(false);
const syncing = ref(false);
const loadingList = ref(false);
const creating = ref(false);
const policies = ref([]);
const currentPolicyName = ref("default");
const showCreate = ref(false);
const newPolicyName = ref("");

const authStore = useAuthStore();
const canEditPolicy = computed(() => authStore.hasPerm("django_ip_safeguard.change_ipguardpolicy"));
const canViewPolicy = computed(() => authStore.hasPerm("django_ip_safeguard.view_ipguardpolicy"));

/** 国家选择项：ISO2 + 本地化国家名（浏览器不支持时退化为 ISO2） */
const countryOptions = computed(() => {
  const lang = String(locale.value || "zh").toLowerCase().startsWith("zh") ? "zh-Hans" : "en";
  let display = null;
  try {
    display = new Intl.DisplayNames([lang], { type: "region" });
  } catch {
    display = null;
  }
  return COUNTRY_ISO2_OPTIONS.map((code) => {
    const name = display ? display.of(code) : "";
    return {
      value: code,
      label: name && name !== code ? `${name} (${code})` : code,
    };
  });
});

const mergeCommonAllowed = () => {
  const s = new Set([...(form.allowed_countries || []), ...COMMON_ISO2]);
  form.allowed_countries = Array.from(s).sort();
};
const clearAllowed = () => {
  form.allowed_countries = [];
};
const clearBlocked = () => {
  form.blocked_countries = [];
};

const syncTierWeightsFromInputs = () => {
  try {
    form.tier_thresholds = JSON.parse(tierJson.value || "{}");
  } catch {
    throw new Error(t("policy.badJsonTier"));
  }
  try {
    form.signal_weights = JSON.parse(weightsJson.value || "{}");
  } catch {
    throw new Error(t("policy.badJsonWeights"));
  }
};

const loadPoliciesList = async () => {
  loadingList.value = true;
  try {
    const data = await listPoliciesApi();
    policies.value = data.items || [];
  } catch {
    policies.value = [];
  } finally {
    loadingList.value = false;
  }
};

const loadDetail = async (name) => {
  const data = await getPolicyByNameApi(name);
  Object.assign(form, emptyForm(), data);
  tierJson.value = JSON.stringify(form.tier_thresholds || {}, null, 0);
  weightsJson.value = JSON.stringify(form.signal_weights || {}, null, 0);
};

const loadPoolStatus = async () => {
  try {
    const data = await getGeoPoolsStatusApi();
    poolMeta.pools = data.pools || [];
  } catch {
    poolMeta.pools = [];
  }
};

const reload = async () => {
  await loadPoliciesList();
  await loadDetail(currentPolicyName.value);
  await loadPoolStatus();
};

const onSelectPolicy = (row) => {
  if (!row?.name) return;
  currentPolicyName.value = row.name;
  loadDetail(row.name).catch(() => {});
};

const onCreatePolicy = async () => {
  const name = (newPolicyName.value || "").trim();
  if (!name) {
    ElMessage.warning(t("policy.newPolicyPlaceholder"));
    return;
  }
  creating.value = true;
  try {
    await createPolicyApi({ name });
    ElMessage.success(t("common.success"));
    showCreate.value = false;
    newPolicyName.value = "";
    await loadPoliciesList();
    currentPolicyName.value = name;
    await loadDetail(name);
  } finally {
    creating.value = false;
  }
};

onMounted(reload);

const onSyncPools = async () => {
  if (!canEditPolicy.value) {
    ElMessage.warning(t("policy.needChangePerm"));
    return;
  }
  syncing.value = true;
  try {
    await syncGeoPoolsApi();
    ElMessage.success(t("common.success"));
    await loadPoolStatus();
  } finally {
    syncing.value = false;
  }
};

const onSave = async () => {
  saving.value = true;
  try {
    if (!canEditPolicy.value) {
      ElMessage.warning(t("policy.noChangePerm"));
      return;
    }
    try {
      syncTierWeightsFromInputs();
    } catch (err) {
      ElMessage.error(err.message || t("common.failed"));
      return;
    }
    const payload = { ...form };
    delete payload.updated_at;
    delete payload.pool_feed_urls;
    delete payload.name;
    await updatePolicyByNameApi(currentPolicyName.value, payload);
    ElMessage.success(t("common.success"));
    await reload();
  } finally {
    saving.value = false;
  }
};
</script>

<style scoped>
.policy-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.history-link {
  font-size: 14px;
}
.policy-list-wrap {
  margin-bottom: 20px;
}
.policy-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
  flex-wrap: wrap;
}
.country-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}
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
</style>
