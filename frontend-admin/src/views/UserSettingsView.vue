<template>
  <div class="page-card" style="max-width: 720px; margin: 0 auto">
    <h2 style="margin-top: 0">{{ t('userSettings.title') }}</h2>

    <el-descriptions :column="1" border style="margin-bottom: 24px">
      <el-descriptions-item :label="t('userSettings.username')">{{ profile.username }}</el-descriptions-item>
      <el-descriptions-item :label="t('userSettings.email')">{{ profile.email || '—' }}</el-descriptions-item>
      <el-descriptions-item :label="t('userSettings.role')">
        <el-tag v-if="profile.is_superuser" type="danger">Superuser</el-tag>
        <el-tag v-else-if="profile.is_staff" type="warning">Staff</el-tag>
        <el-tag v-else>User</el-tag>
      </el-descriptions-item>
      <el-descriptions-item :label="t('userSettings.twoFactor')">
        <el-tag :type="profile.two_factor_enabled ? 'success' : 'info'">
          {{ profile.two_factor_enabled ? t('common.enabled') : t('common.disabled') }}
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item :label="t('userSettings.dateJoined')">{{ profile.date_joined || '—' }}</el-descriptions-item>
      <el-descriptions-item :label="t('userSettings.lastLogin')">{{ profile.last_login || '—' }}</el-descriptions-item>
    </el-descriptions>

    <el-tabs v-model="activeTab">
      <el-tab-pane :label="t('userSettings.changePassword')" name="password">
        <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="140px" style="max-width: 500px">
          <el-form-item :label="t('userSettings.oldPassword')" prop="old_password">
            <el-input v-model="passwordForm.old_password" type="password" show-password />
          </el-form-item>
          <el-form-item :label="t('userSettings.newPassword')" prop="new_password">
            <el-input v-model="passwordForm.new_password" type="password" show-password />
            <div v-if="passwordForm.new_password" style="margin-top: 8px">
              <div style="display: flex; gap: 4px; margin-bottom: 4px">
                <div v-for="i in 4" :key="i" :style="{
                  flex: 1,
                  height: '4px',
                  borderRadius: '2px',
                  background: i <= passwordStrength.level ? passwordStrength.color : '#e4e7ed',
                  transition: 'background 0.3s',
                }" />
              </div>
              <span :style="{ color: passwordStrength.color, fontSize: '12px' }">{{ passwordStrength.label }}</span>
            </div>
          </el-form-item>
          <el-form-item :label="t('userSettings.confirmPassword')" prop="confirm_password">
            <el-input v-model="passwordForm.confirm_password" type="password" show-password />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="passwordLoading" @click="onChangePassword">
              {{ t('common.save') }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane :label="t('userSettings.changeEmail')" name="email">
        <div v-if="profile.pending_email" style="margin-bottom: 16px">
          <el-alert
            type="warning"
            :title="t('userSettings.emailVerificationHint', { email: profile.pending_email })"
            show-icon
            :closable="false"
          >
            <template #extra>
              <el-button type="warning" size="small" :loading="emailResendLoading" @click="onResendVerification" style="margin-left: 12px">
                {{ t('userSettings.emailResend') }}
              </el-button>
            </template>
          </el-alert>
        </div>
        <el-form ref="emailFormRef" :model="emailForm" :rules="emailRules" label-width="140px" style="max-width: 500px">
          <el-form-item :label="t('userSettings.currentEmail')">
            <span>{{ profile.email || '—' }}</span>
          </el-form-item>
          <el-form-item :label="t('userSettings.newEmail')" prop="email">
            <el-input v-model="emailForm.email" type="email" :placeholder="profile.pending_email ? profile.pending_email : ''" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="emailLoading" @click="onChangeEmail">
              {{ t('common.save') }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane :label="t('userSettings.twoFactorAuth')" name="2fa">
        <div style="margin-bottom: 16px">
          <el-alert
            :type="twoFactorEnabled ? 'success' : 'info'"
            :title="twoFactorEnabled ? t('userSettings.twoFactorEnabled') : t('userSettings.twoFactorDisabled')"
            show-icon
            :closable="false"
          />
        </div>

        <template v-if="!twoFactorEnabled && !setupData">
          <el-button type="primary" @click="onSetup2FA" :loading="setupLoading">
            {{ t('userSettings.enable2FA') }}
          </el-button>
        </template>

        <template v-if="setupData">
          <el-card style="margin-bottom: 16px">
            <p style="margin-top: 0; font-weight: 600">{{ t('userSettings.scanQRCode') }}</p>
            <p>{{ t('userSettings.secretKey') }}: <code style="background: #f0f0f0; padding: 2px 6px; border-radius: 4px">{{ setupData.secret }}</code></p>
            <div style="margin: 12px 0">
              <img :src="qrCodeUrl" alt="QR Code" style="border: 4px solid #fff" v-if="qrCodeUrl" />
            </div>
            <el-form :model="verifyForm" label-width="140px" style="max-width: 400px">
              <el-form-item :label="t('userSettings.verificationCode')">
                <el-input v-model="verifyForm.code" :placeholder="t('userSettings.enterCode')" style="width: 200px" />
              </el-form-item>
              <el-form-item>
                <el-button type="success" @click="onVerify2FA" :loading="verifyLoading">
                  {{ t('userSettings.confirmEnable') }}
                </el-button>
                <el-button @click="setupData = null">{{ t('common.cancel') }}</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </template>

        <template v-if="twoFactorEnabled">
          <el-divider />
          <h4>{{ t('userSettings.disable2FA') }}</h4>
          <el-form :model="disableForm" label-width="140px" style="max-width: 400px">
            <el-form-item :label="t('userSettings.verificationCode')">
              <el-input v-model="disableForm.code" :placeholder="t('userSettings.enterCode')" style="width: 200px" />
            </el-form-item>
            <el-form-item>
              <el-button type="danger" @click="onDisable2FA" :loading="disableLoading">
                {{ t('userSettings.confirmDisable') }}
              </el-button>
            </el-form-item>
          </el-form>
        </template>
      </el-tab-pane>

      <el-tab-pane :label="t('userSettings.apiKeys')" name="apikey">
        <div style="margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center">
          <span style="color: #606266; font-size: 14px">{{ t('userSettings.noApiKeys') }}</span>
          <el-button type="primary" @click="showCreateDialog = true">
            {{ t('userSettings.createApiKey') }}
          </el-button>
        </div>

        <el-table :data="apiKeyList" style="width: 100%" v-if="apiKeyList.length > 0" stripe>
          <el-table-column prop="name" :label="t('userSettings.apiKeyName')" width="140" />
          <el-table-column prop="prefix" :label="t('userSettings.apiKeyPrefix')" width="100" />
          <el-table-column :label="t('userSettings.apiKeyStatus')" width="90">
            <template #default="{ row }">
              <el-tag v-if="!row.is_active" type="info" size="small">{{ t('userSettings.apiKeyRevoked') }}</el-tag>
              <el-tag v-else-if="row.expires_at && new Date(row.expires_at) < new Date()" type="warning" size="small">{{ t('userSettings.apiKeyExpired') }}</el-tag>
              <el-tag v-else type="success" size="small">{{ t('userSettings.apiKeyActive') }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('userSettings.apiKeyExpires')" width="170">
            <template #default="{ row }">
              {{ row.expires_at ? new Date(row.expires_at).toLocaleString() : t('userSettings.apiKeyNoExpiry') }}
            </template>
          </el-table-column>
          <el-table-column :label="t('userSettings.apiKeyLastUsed')" width="170">
            <template #default="{ row }">
              {{ row.last_used_at ? new Date(row.last_used_at).toLocaleString() : '—' }}
            </template>
          </el-table-column>
          <el-table-column :label="t('userSettings.apiKeyCreatedAt')" width="170">
            <template #default="{ row }">
              {{ row.created_at ? new Date(row.created_at).toLocaleString() : '—' }}
            </template>
          </el-table-column>
          <el-table-column :label="t('common.action')" width="100" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.is_active"
                type="danger"
                size="small"
                link
                @click="onRevokeApiKey(row)"
              >
                {{ t('userSettings.revokeApiKey') }}
              </el-button>
              <span v-else style="color: #909399; font-size: 12px">—</span>
            </template>
          </el-table-column>
        </el-table>

        <el-dialog v-model="showCreateDialog" :title="t('userSettings.createApiKey')" width="460px" :close-on-click-modal="false">
          <el-form :model="apiKeyCreateForm" label-width="120px">
            <el-form-item :label="t('userSettings.apiKeyName')">
              <el-input v-model="apiKeyCreateForm.name" :placeholder="t('userSettings.apiKeyNamePlaceholder')" />
            </el-form-item>
            <el-form-item :label="t('userSettings.apiKeyExpiresDays')">
              <el-input-number v-model="apiKeyCreateForm.expires_days" :min="0" :max="3650" />
              <div style="margin-top: 4px; font-size: 12px; color: #909399">{{ t('userSettings.apiKeyExpiresDaysHint') }}</div>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showCreateDialog = false">{{ t('common.cancel') }}</el-button>
            <el-button type="primary" :loading="apiKeyCreating" @click="onCreateApiKey">{{ t('common.save') }}</el-button>
          </template>
        </el-dialog>

        <el-dialog v-model="showKeyDialog" :title="t('userSettings.apiKeyCreated')" width="520px" :close-on-click-modal="false" :show-close="true" @close="onKeyDialogClose">
          <el-alert type="warning" :title="t('userSettings.apiKeyWarning')" show-icon :closable="false" style="margin-bottom: 16px" />
          <el-input
            v-model="newKeyValue"
            readonly
            type="textarea"
            :rows="3"
          />
          <template #footer>
            <el-button type="primary" @click="onCopyKey">{{ t('common.copy') || 'Copy' }}</el-button>
          </template>
        </el-dialog>

        <el-dialog v-model="showRecoveryCodesDialog" :title="t('userSettings.recoveryCodesTitle')" width="480px" :close-on-click-modal="false" :show-close="true">
          <el-alert type="warning" :title="t('userSettings.recoveryCodesHint')" show-icon :closable="false" style="margin-bottom: 16px" />
          <div style="display: flex; flex-wrap: wrap; gap: 8px; justify-content: center">
            <code v-for="code in recoveryCodes" :key="code" style="background: #f0f0f0; padding: 8px 16px; border-radius: 6px; font-size: 18px; letter-spacing: 2px; font-weight: 600; color: #409eff">{{ code }}</code>
          </div>
          <template #footer>
            <el-button type="primary" @click="onCopyRecoveryCodes">{{ t('common.copy') }}</el-button>
            <el-button type="success" @click="showRecoveryCodesDialog = false">{{ t('common.confirm') || 'OK' }}</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from "vue";
import { useI18n } from "vue-i18n";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  userProfileApi,
  changePasswordApi,
  changeEmailApi,
  twoFactorStatusApi,
  twoFactorSetupApi,
  twoFactorVerifyApi,
  twoFactorDisableApi,
  apiKeyListApi,
  apiKeyCreateApi,
  apiKeyRevokeApi,
} from "../api";

const { t } = useI18n();

const activeTab = ref("password");
const profile = ref({
  username: "",
  email: "",
  is_staff: false,
  is_superuser: false,
  two_factor_enabled: false,
  date_joined: null,
  last_login: null,
});

const twoFactorEnabled = ref(false);
const setupData = ref(null);
const qrCodeUrl = ref("");

const passwordFormRef = ref(null);
const emailFormRef = ref(null);
const passwordLoading = ref(false);
const emailLoading = ref(false);
const emailResendLoading = ref(false);
const setupLoading = ref(false);
const verifyLoading = ref(false);
const disableLoading = ref(false);

const passwordForm = reactive({
  old_password: "",
  new_password: "",
  confirm_password: "",
});

const emailForm = reactive({
  email: "",
});

const verifyForm = reactive({ code: "" });
const disableForm = reactive({ code: "" });

const passwordStrength = computed(() => {
  const pw = passwordForm.new_password;
  if (!pw) return { level: 0, color: "#e4e7ed", label: "" };
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^a-zA-Z0-9]/.test(pw)) score++;
  const levels = [
    { level: 0, color: "#f56c6c", label: t("userSettings.veryWeak") },
    { level: 1, color: "#f56c6c", label: t("userSettings.weak") },
    { level: 2, color: "#e6a23c", label: t("userSettings.medium") },
    { level: 3, color: "#67c23a", label: t("userSettings.strong") },
    { level: 4, color: "#409eff", label: t("userSettings.veryStrong") },
  ];
  return levels[score] || levels[0];
});

const validateConfirmPassword = (_rule, value, callback) => {
  if (value !== passwordForm.new_password) {
    callback(new Error(t("userSettings.passwordMismatch")));
  } else {
    callback();
  }
};

const passwordRules = computed(() => ({
  old_password: [{ required: true, message: t("userSettings.oldPasswordRequired"), trigger: "blur" }],
  new_password: [
    { required: true, message: t("userSettings.newPasswordRequired"), trigger: "blur" },
    { min: 8, message: t("userSettings.passwordMinLength"), trigger: "blur" },
  ],
  confirm_password: [
    { required: true, message: t("userSettings.confirmPasswordRequired"), trigger: "blur" },
    { validator: validateConfirmPassword, trigger: "blur" },
  ],
}));

const emailRules = computed(() => ({
  email: [
    { required: true, message: t("userSettings.emailRequired"), trigger: "blur" },
    { type: "email", message: t("userSettings.emailInvalid"), trigger: "blur" },
  ],
}));

async function fetchProfile() {
  try {
    const data = await userProfileApi();
    profile.value = data;
    twoFactorEnabled.value = data.two_factor_enabled;
  } catch {
    ElMessage.error(t("common.failed"));
  }
}

async function fetch2FAStatus() {
  try {
    const data = await twoFactorStatusApi();
    twoFactorEnabled.value = data.enabled;
  } catch {
    // ignore
  }
}

async function onChangePassword() {
  try {
    await passwordFormRef.value.validate();
  } catch {
    return;
  }
  passwordLoading.value = true;
  try {
    await changePasswordApi({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    });
    ElMessage.success(t("userSettings.passwordChanged"));
    passwordForm.old_password = "";
    passwordForm.new_password = "";
    passwordForm.confirm_password = "";
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || t("common.failed"));
  } finally {
    passwordLoading.value = false;
  }
}

async function onChangeEmail() {
  try {
    await emailFormRef.value.validate();
  } catch {
    return;
  }
  emailLoading.value = true;
  try {
    await changeEmailApi({ email: emailForm.email });
    profile.value.pending_email = emailForm.email;
    ElMessage.success(t("userSettings.emailChangeSuccess"));
    emailForm.email = "";
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || t("common.failed"));
  } finally {
    emailLoading.value = false;
  }
}

async function onResendVerification() {
  if (!profile.value.pending_email) return;
  emailResendLoading.value = true;
  try {
    await changeEmailApi({ email: profile.value.pending_email });
    ElMessage.success(t("userSettings.emailChangeSuccess"));
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || t("common.failed"));
  } finally {
    emailResendLoading.value = false;
  }
}

async function onSetup2FA() {
  setupLoading.value = true;
  try {
    const data = await twoFactorSetupApi();
    setupData.value = data;
    const QRCode = (await import("qrcode")).default;
    qrCodeUrl.value = await QRCode.toDataURL(data.provisioning_uri, { width: 200 });
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || t("common.failed"));
  } finally {
    setupLoading.value = false;
  }
}

async function onVerify2FA() {
  if (!verifyForm.code.trim()) {
    ElMessage.warning(t("userSettings.enterCode"));
    return;
  }
  verifyLoading.value = true;
  try {
    const data = await twoFactorVerifyApi({ code: verifyForm.code });
    twoFactorEnabled.value = true;
    profile.value.two_factor_enabled = true;
    setupData.value = null;
    qrCodeUrl.value = "";
    verifyForm.code = "";
    if (data.recovery_codes && data.recovery_codes.length > 0) {
      recoveryCodes.value = data.recovery_codes;
      showRecoveryCodesDialog.value = true;
    } else {
      ElMessage.success(t("userSettings.twoFactorEnabled"));
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || t("common.failed"));
  } finally {
    verifyLoading.value = false;
  }
}

async function onDisable2FA() {
  if (!disableForm.code.trim()) {
    ElMessage.warning(t("userSettings.enterCode"));
    return;
  }
  disableLoading.value = true;
  try {
    await twoFactorDisableApi({ code: disableForm.code });
    twoFactorEnabled.value = false;
    profile.value.two_factor_enabled = false;
    disableForm.code = "";
    ElMessage.success(t("userSettings.twoFactorDisabled"));
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || t("common.failed"));
  } finally {
    disableLoading.value = false;
  }
}

const recoveryCodes = ref([]);
const showRecoveryCodesDialog = ref(false);

const apiKeyList = ref([]);
const showCreateDialog = ref(false);
const showKeyDialog = ref(false);
const apiKeyCreating = ref(false);
const newKeyValue = ref("");
const apiKeyCreateForm = reactive({
  name: "",
  expires_days: 0,
});

async function fetchApiKeys() {
  try {
    const data = await apiKeyListApi();
    apiKeyList.value = Array.isArray(data) ? data : [];
  } catch {
    // ignore
  }
}

async function onCreateApiKey() {
  apiKeyCreating.value = true;
  try {
    const data = await apiKeyCreateApi({
      name: apiKeyCreateForm.name || "default",
      expires_days: apiKeyCreateForm.expires_days,
    });
    newKeyValue.value = data.key;
    showCreateDialog.value = false;
    showKeyDialog.value = true;
    apiKeyCreateForm.name = "";
    apiKeyCreateForm.expires_days = 0;
    await fetchApiKeys();
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || t("common.failed"));
  } finally {
    apiKeyCreating.value = false;
  }
}

async function onRevokeApiKey(row) {
  try {
    await ElMessageBox.confirm(t("userSettings.revokeConfirm"), t("common.confirm"), {
      confirmButtonText: t("common.confirm"),
      cancelButtonText: t("common.cancel"),
      type: "warning",
    });
  } catch {
    return;
  }
  try {
    await apiKeyRevokeApi({ id: row.id });
    ElMessage.success(t("userSettings.apiKeyRevoked"));
    await fetchApiKeys();
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || t("common.failed"));
  }
}

async function onCopyKey() {
  try {
    await navigator.clipboard.writeText(newKeyValue.value);
    ElMessage.success(t("userSettings.apiKeyCopySuccess"));
  } catch {
    ElMessage.error(t("userSettings.apiKeyCopyFailed"));
  }
}

function onKeyDialogClose() {
  newKeyValue.value = "";
}

async function onCopyRecoveryCodes() {
  try {
    await navigator.clipboard.writeText(recoveryCodes.value.join("\n"));
    ElMessage.success(t("userSettings.recoveryCodeCopied"));
  } catch {
    ElMessage.error(t("userSettings.apiKeyCopyFailed"));
  }
}

onMounted(() => {
  fetchProfile();
  fetch2FAStatus();
  fetchApiKeys();
});
</script>
