<template>
  <div class="page-card" style="max-width: 900px; margin: 0 auto">
    <h2 style="margin-top: 0">{{ t('systemSettings.title') }}</h2>

    <el-tabs v-model="activeTab">
      <el-tab-pane :label="t('systemSettings.general')" name="general">
        <el-form :model="settingsForm" label-width="200px" style="max-width: 600px">
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
        <el-form ref="settingsFormRef" :model="settingsForm" label-width="200px" style="max-width: 600px" :disabled="!hasChangePerm">
          <el-form-item :label="t('systemSettings.riskScoreThreshold')">
            <el-input-number v-model="settingsForm.risk_score_threshold" :min="0" :max="100" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.rateLimitPerMinute')">
            <el-input-number v-model="settingsForm.rate_limit_per_minute" :min="0" :max="100000" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.blockStatusCode')">
            <el-input-number v-model="settingsForm.block_status_code" :min="400" :max="499" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.failOpen')">
            <el-switch v-model="settingsForm.fail_open" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.useDbLog')">
            <el-switch v-model="settingsForm.use_db_log" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.cacheTtl')">
            <el-input-number v-model="settingsForm.cache_ttl" :min="60" :max="86400" />
          </el-form-item>
          <el-form-item :label="t('systemSettings.banTtl')">
            <el-input-number v-model="settingsForm.ban_ttl" :min="60" :max=2592000 />
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
        <el-form :model="settingsForm" label-width="200px" style="max-width: 600px" :disabled="!hasChangePerm">
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
  china_pool_rule: "off",
  international_pool_rule: "off",
  ip_mask_enabled: false,
  ip_mask_keep_prefix: 24,
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
    const data = await getSystemSettingsApi();
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
