<template>
  <div class="page-card" style="max-width: 1200px; margin: 0 auto">
    <h2 style="margin-top: 0">{{ t('systemSettings.title') }}</h2>

    <el-tabs v-model="activeTab">
      <el-tab-pane :label="t('systemSettings.general')" name="general">
        <el-form :model="settingsForm" label-width="220px" style="max-width: 700px">
          <el-form-item :label="t('systemSettings.defaultLanguage')">
            <el-select v-model="languageForm.language" @change="onLanguageChange" style="width: 240px">
              <el-option v-for="lang in i18nStore.languages" :key="lang.code" :label="lang.name" :value="lang.code" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('systemSettings.theme')">
            <el-radio-group v-model="themeStore.theme" @change="themeStore.setTheme">
              <el-radio-button v-for="opt in themeStore.themeOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item :label="t('systemSettings.primaryColor')">
            <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center">
              <div
                v-for="color in themeStore.colorOptions"
                :key="color.value"
                :style="{
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  background: color.value,
                  cursor: 'pointer',
                  border: themeStore.primaryColor === color.value ? '3px solid var(--el-color-primary)' : '2px solid #dcdfe6',
                  transition: 'border 0.2s',
                }"
                :title="color.label"
                @click="themeStore.setPrimaryColor(color.value)"
              />
              <el-divider direction="vertical" />
              <el-color-picker
                v-model="customColor"
                @change="onCustomColorChange"
                :predefine="themeStore.colorOptions.map(c => c.value)"
              />
            </div>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane :label="t('systemSettings.security')" name="security">
        <el-form ref="settingsFormRef" :model="settingsForm" label-width="220px" style="max-width: 700px" :disabled="!hasChangePerm">
          <el-divider content-position="left">{{ t('systemSettings.riskSettings') }}</el-divider>
          <el-form-item :label="t('systemSettings.riskScoreThreshold')">
            <el-input-number v-model="settingsForm.risk_score_threshold" :min="0" :max="100" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.localRiskEngine')">
            <el-switch v-model="settingsForm.local_risk_engine_enabled" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.subnetAttackThreshold')">
            <el-input-number v-model="settingsForm.local_risk_subnet_attack_threshold" :min="2" :max="100" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.ipCorrelation')">
            <el-switch v-model="settingsForm.ip_correlation_enabled" />
          </el-form-item>

          <el-divider content-position="left">{{ t('systemSettings.blockSettings') }}</el-divider>
          <el-form-item :label="t('systemSettings.rateLimitPerMinute')">
            <el-input-number v-model="settingsForm.rate_limit_per_minute" :min="0" :max="100000" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.blockStatusCode')">
            <el-input-number v-model="settingsForm.block_status_code" :min="400" :max="499" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.failOpen')">
            <el-switch v-model="settingsForm.fail_open" />
          </el-form-item>

          <el-divider content-position="left">{{ t('systemSettings.cacheSettings') }}</el-divider>
          <el-form-item :label="t('systemSettings.l1CacheEnabled')">
            <el-switch v-model="settingsForm.l1_cache_enabled" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.l1CacheTtl')">
            <el-input-number v-model="settingsForm.l1_cache_ttl" :min="1" :max="60" /> {{ t('systemSettings.seconds') }}
          </el-form-item>
          <el-form-item :label="t('systemSettings.l1CacheMaxSize')">
            <el-input-number v-model="settingsForm.l1_cache_max_size" :min="100" :max="100000" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.cacheTtl')">
            <el-input-number v-model="settingsForm.cache_ttl" :min="60" :max="86400" /> {{ t('systemSettings.seconds') }}
          </el-form-item>
          <el-form-item :label="t('systemSettings.highRiskCacheTtl')">
            <el-input-number v-model="settingsForm.high_risk_cache_ttl" :min="60" :max="86400" /> {{ t('systemSettings.seconds') }}
          </el-form-item>
          <el-form-item :label="t('systemSettings.lowRiskCacheTtl')">
            <el-input-number v-model="settingsForm.low_risk_cache_ttl" :min="60" :max="86400" /> {{ t('systemSettings.seconds') }}
          </el-form-item>
          <el-form-item :label="t('systemSettings.banTtl')">
            <el-input-number v-model="settingsForm.ban_ttl" :min="60" :max="2592000" /> {{ t('systemSettings.seconds') }}
          </el-form-item>

          <el-divider content-position="left">{{ t('systemSettings.advancedSettings') }}</el-divider>
          <el-form-item :label="t('systemSettings.circuitBreakerFailures')">
            <el-input-number v-model="settingsForm.provider_circuit_breaker_failures" :min="1" :max="50" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.circuitBreakerTtl')">
            <el-input-number v-model="settingsForm.provider_circuit_breaker_ttl" :min="10" :max="300" /> {{ t('systemSettings.seconds') }}
          </el-form-item>
          <el-form-item :label="t('systemSettings.dedupeLockSeconds')">
            <el-input-number v-model="settingsForm.dedupe_lock_seconds" :min="1" :max="30" /> {{ t('systemSettings.seconds') }}
          </el-form-item>

          <el-divider content-position="left">{{ t('systemSettings.auditSettings') }}</el-divider>
          <el-form-item :label="t('systemSettings.useDbLog')">
            <el-switch v-model="settingsForm.use_db_log" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.ipMaskEnabled')">
            <el-switch v-model="settingsForm.ip_mask_enabled" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.ipMaskKeepPrefix')">
            <el-input-number v-model="settingsForm.ip_mask_keep_prefix" :min="0" :max="32" />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="saveLoading" @click="onSaveSettings">
              {{ t('common.save') }}
            </el-button>
          </el-form-item>
        </el-form>
        <el-alert
          v-if="!hasChangePerm"
          :title="t('policy.viewOnlyHint')"
          type="warning"
          show-icon
          :closable="false"
          style="margin-top: 12px"
        />
      </el-tab-pane>

      <el-tab-pane :label="t('systemSettings.geoPool')" name="geoPool">
        <el-form :model="settingsForm" label-width="220px" style="max-width: 700px" :disabled="!hasChangePerm">
          <el-form-item :label="t('policy.chinaPoolRule')">
            <el-select v-model="settingsForm.china_pool_rule" style="width: 240px">
              <el-option value="off" :label="t('policy.poolRuleOff')" />
              <el-option value="allow_only_in_pool" :label="t('policy.poolRuleAllowOnlyShort')" />
              <el-option value="block_in_pool" :label="t('policy.poolRuleBlock')" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('policy.internationalPoolRule')">
            <el-select v-model="settingsForm.international_pool_rule" style="width: 240px">
              <el-option value="off" :label="t('policy.poolRuleOff')" />
              <el-option value="allow_only_in_pool" :label="t('policy.poolRuleAllowOnlyShort')" />
              <el-option value="block_in_pool" :label="t('policy.poolRuleBlock')" />
            </el-select>
          </el-form-item>
          <el-divider content-position="left">{{ t('systemSettings.dataSourceConfig') }}</el-divider>
          <el-form-item :label="t('systemSettings.multiSourceEnabled')">
            <el-switch v-model="settingsForm.geo_pool_multi_source_enabled" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.chinaPoolUrl')">
            <el-input :value="settingsForm.geo_china_pool_url" disabled />
          </el-form-item>
          <el-form-item :label="t('systemSettings.internationalPoolUrl')">
            <el-input :value="settingsForm.geo_international_pool_url" disabled />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saveLoading" @click="onSaveSettings">
              {{ t('common.save') }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane :label="t('systemSettings.threatIntel')" name="threatIntel">
        <el-form :model="settingsForm" label-width="220px" style="max-width: 700px" :disabled="!hasChangePerm">
          <el-form-item :label="t('systemSettings.threatIntelEnabled')">
            <el-switch v-model="settingsForm.threat_intel_enabled" />
          </el-form-item>
          <el-divider content-position="left">{{ t('systemSettings.intelSources') }}</el-divider>
          <el-form-item :label="t('systemSettings.spamhausEnabled')">
            <el-switch v-model="settingsForm.threat_intel_spamhaus_enabled" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.torEnabled')">
            <el-switch v-model="settingsForm.threat_intel_tor_enabled" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.emergingEnabled')">
            <el-switch v-model="settingsForm.threat_intel_emerging_enabled" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saveLoading" @click="onSaveSettings">
              {{ t('common.save') }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane :label="t('systemSettings.geoip2')" name="geoip2">
        <el-form :model="settingsForm" label-width="220px" style="max-width: 700px" :disabled="!hasChangePerm">
          <el-form-item :label="t('systemSettings.geoip2Enabled')">
            <el-switch v-model="settingsForm.geoip2_enabled" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.geoip2CityDb')">
            <el-input :value="settingsForm.geoip2_city_db_path" disabled />
          </el-form-item>
          <el-form-item :label="t('systemSettings.geoip2AsnDb')">
            <el-input :value="settingsForm.geoip2_asn_db_path" disabled />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saveLoading" @click="onSaveSettings">
              {{ t('common.save') }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane :label="t('systemSettings.provider')" name="provider">
        <el-form :model="settingsForm" label-width="220px" style="max-width: 700px" :disabled="!hasChangePerm">
          <el-form-item :label="t('systemSettings.currentProvider')">
            <el-input :value="settingsForm.provider" disabled />
          </el-form-item>
          <el-form-item :label="t('systemSettings.providerEndpoint')">
            <el-input :value="settingsForm.provider_endpoint" disabled />
          </el-form-item>
          <el-form-item :label="t('systemSettings.providerTimeout')">
            <el-input-number :model-value="settingsForm.provider_timeout" disabled /> {{ t('systemSettings.seconds') }}
          </el-form-item>
          <el-form-item :label="t('systemSettings.providerMaxRetries')">
            <el-input-number :model-value="settingsForm.provider_max_retries" disabled />
          </el-form-item>
          <el-divider content-position="left">{{ t('systemSettings.providerChain') }}</el-divider>
          <el-form-item :label="t('systemSettings.providerChainEnabled')">
            <el-switch v-model="settingsForm.provider_chain_enabled" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.providerChainNames')">
            <el-input :value="settingsForm.provider_chain_names.join(', ')" disabled />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saveLoading" @click="onSaveSettings">
              {{ t('common.save') }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane :label="t('systemSettings.auth')" name="auth">
        <el-form :model="settingsForm" label-width="220px" style="max-width: 700px" :disabled="!hasChangePerm">
          <el-divider content-position="left">{{ t('systemSettings.loginSecurity') }}</el-divider>
          <el-form-item :label="t('systemSettings.loginFailLimit')">
            <el-input-number v-model="settingsForm.login_fail_limit" :min="0" :max="100" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.loginFailLockSeconds')">
            <el-input-number v-model="settingsForm.login_fail_lock_seconds" :min="60" :max="86400" /> {{ t('systemSettings.seconds') }}
          </el-form-item>
          <el-form-item :label="t('systemSettings.passwordMaxAge')">
            <el-input-number v-model="settingsForm.password_max_age_days" :min="0" :max="3650" /> {{ t('systemSettings.days') }}
          </el-form-item>
          <el-divider content-position="left">JWT</el-divider>
          <el-form-item :label="t('systemSettings.jwtAccessTtl')">
            <el-input-number :model-value="settingsForm.jwt_access_token_ttl_seconds / 3600" disabled /> {{ t('systemSettings.hours') }}
          </el-form-item>
          <el-form-item :label="t('systemSettings.jwtRefreshTtl')">
            <el-input-number :model-value="Math.round(settingsForm.jwt_refresh_token_ttl_seconds / 86400)" disabled /> {{ t('systemSettings.days') }}
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saveLoading" @click="onSaveSettings">
              {{ t('common.save') }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane :label="t('systemSettings.ipReputation')" name="ipReputation">
        <el-form :model="settingsForm" label-width="220px" style="max-width: 700px" :disabled="!hasChangePerm">
          <el-form-item :label="t('systemSettings.ipReputationEnabled')">
            <el-switch v-model="settingsForm.ip_reputation_enabled" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.snapshotInterval')">
            <el-input-number v-model="settingsForm.ip_reputation_snapshot_interval" :min="300" :max="86400" /> {{ t('systemSettings.seconds') }}
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saveLoading" @click="onSaveSettings">
              {{ t('common.save') }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from "vue";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import { useThemeStore } from "../stores/theme";
import { useI18nStore } from "../stores/i18n";
import { useAuthStore } from "../stores/auth";
import { getSystemSettingsApi, updateSystemSettingsApi } from "../api";

const { t } = useI18n();
const themeStore = useThemeStore();
const i18nStore = useI18nStore();
const authStore = useAuthStore();

const activeTab = ref("general");
const saveLoading = ref(false);
const customColor = ref(themeStore.primaryColor);

const languageForm = reactive({
  language: i18nStore.currentLocale,
});

const settingsForm = reactive({
  risk_score_threshold: 70,
  rate_limit_per_minute: 0,
  block_status_code: 403,
  fail_open: true,
  use_db_log: false,
  cache_ttl: 3600,
  ban_ttl: 86400,
  login_fail_limit: 5,
  login_fail_lock_seconds: 300,
  password_max_age_days: 0,
  china_pool_rule: "off",
  international_pool_rule: "off",
  ip_mask_enabled: true,
  ip_mask_keep_prefix: 2,
  l1_cache_enabled: true,
  l1_cache_ttl: 10,
  l1_cache_max_size: 10000,
  local_risk_engine_enabled: true,
  local_risk_subnet_attack_threshold: 10,
  ip_correlation_enabled: true,
  threat_intel_enabled: false,
  threat_intel_spamhaus_enabled: true,
  threat_intel_tor_enabled: true,
  threat_intel_emerging_enabled: true,
  geoip2_enabled: false,
  geoip2_city_db_path: "",
  geoip2_asn_db_path: "",
  provider_chain_enabled: false,
  provider_chain_names: [],
  geo_pool_multi_source_enabled: true,
  geo_china_pool_url: "",
  geo_international_pool_url: "",
  provider_circuit_breaker_failures: 5,
  provider_circuit_breaker_ttl: 60,
  high_risk_cache_ttl: 7200,
  low_risk_cache_ttl: 1800,
  dedupe_lock_seconds: 3,
  provider: "",
  provider_endpoint: "",
  provider_timeout: 3.0,
  provider_max_retries: 2,
  jwt_access_token_ttl_seconds: 7200,
  jwt_refresh_token_ttl_seconds: 604800,
  ip_reputation_enabled: true,
  ip_reputation_snapshot_interval: 3600,
});

const hasChangePerm = computed(() => authStore.hasPerm("django_ip_safeguard.change_ipguardpolicy"));

function onLanguageChange(lang) {
  i18nStore.switchLocale(lang);
}

function onCustomColorChange(val) {
  if (val) {
    themeStore.setPrimaryColor(val);
  }
}

async function fetchSettings() {
  try {
    const res = await getSystemSettingsApi();
    const data = res.data || res;
    Object.keys(settingsForm).forEach((key) => {
      if (data[key] !== undefined) {
        settingsForm[key] = data[key];
      }
    });
  } catch {
    // ignore
  }
}

async function onSaveSettings() {
  saveLoading.value = true;
  try {
    await updateSystemSettingsApi({ ...settingsForm });
    ElMessage.success(t("common.success"));
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || t("common.failed"));
  } finally {
    saveLoading.value = false;
  }
}

onMounted(() => {
  fetchSettings();
});
</script>
