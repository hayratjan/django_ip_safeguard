<template>
  <div class="page-card">
    <h3>{{ t("systemUsers.title") }}</h3>
    <p class="intro">{{ t("systemUsers.intro") }}</p>
    <el-space wrap style="margin-bottom: 12px">
      <el-button type="primary" link @click="openDjangoAdmin">{{ t("systemUsers.openDjangoAdmin") }}</el-button>
    </el-space>

    <el-space wrap style="margin-bottom: 12px">
      <el-input v-model="query.q" :placeholder="t('systemUsers.searchPlaceholder')" style="width: 220px" clearable />
      <el-button @click="onSearch">{{ t("common.query") }}</el-button>
      <el-button v-if="canAdd" type="primary" @click="openCreate">{{ t("systemUsers.createUser") }}</el-button>
    </el-space>

    <el-table v-loading="loading" :data="items" size="small">
      <el-table-column prop="username" :label="t('systemUsers.username')" width="140" />
      <el-table-column prop="email" :label="t('systemUsers.email')" min-width="160" show-overflow-tooltip />
      <el-table-column prop="is_staff" :label="t('systemUsers.staff')" width="70">
        <template #default="{ row }">{{ row.is_staff ? t("common.yes") : t("common.no") }}</template>
      </el-table-column>
      <el-table-column prop="is_superuser" :label="t('systemUsers.superuser')" width="90">
        <template #default="{ row }">{{ row.is_superuser ? t("common.yes") : t("common.no") }}</template>
      </el-table-column>
      <el-table-column prop="is_active" :label="t('systemUsers.active')" width="70">
        <template #default="{ row }">{{ row.is_active ? t("common.yes") : t("common.no") }}</template>
      </el-table-column>
      <el-table-column prop="last_login" :label="t('systemUsers.lastLogin')" width="180" />
      <el-table-column :label="t('systemUsers.groups')" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ (row.groups || []).map((g) => g.name).join(", ") }}</template>
      </el-table-column>
      <el-table-column v-if="canChange" :label="t('common.actions')" width="90">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">{{ t("systemUsers.editUser") }}</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      style="margin-top: 12px; justify-content: flex-end"
      layout="total, sizes, prev, pager, next"
      :total="total"
      :page-sizes="[10, 20, 50]"
      @current-change="load"
      @size-change="onSizeChange"
    />

    <el-dialog v-model="createVisible" :title="t('systemUsers.createUser')" width="480px" destroy-on-close @closed="resetCreate">
      <el-form label-width="100px">
        <el-form-item :label="t('systemUsers.username')" required>
          <el-input v-model="createForm.username" autocomplete="off" />
        </el-form-item>
        <el-form-item :label="t('systemUsers.password')" required>
          <el-input v-model="createForm.password" type="password" show-password autocomplete="new-password" />
        </el-form-item>
        <el-form-item :label="t('systemUsers.email')">
          <el-input v-model="createForm.email" autocomplete="off" />
        </el-form-item>
        <el-form-item :label="t('systemUsers.staff')">
          <el-switch v-model="createForm.is_staff" />
        </el-form-item>
        <el-form-item v-if="authStore.user?.is_superuser" :label="t('systemUsers.superuser')">
          <el-switch v-model="createForm.is_superuser" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">{{ t("systemUsers.cancel") }}</el-button>
        <el-button type="primary" :loading="createSaving" @click="submitCreate">{{ t("common.save") }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" :title="t('systemUsers.editUser')" width="520px" destroy-on-close>
      <el-form v-if="editForm" label-width="110px">
        <el-form-item :label="t('systemUsers.username')">
          <span>{{ editForm.username }}</span>
        </el-form-item>
        <el-form-item :label="t('systemUsers.email')">
          <el-input v-model="editForm.email" autocomplete="off" />
        </el-form-item>
        <el-form-item :label="t('systemUsers.staff')">
          <el-switch v-model="editForm.is_staff" />
        </el-form-item>
        <el-form-item v-if="authStore.user?.is_superuser" :label="t('systemUsers.superuser')">
          <el-switch v-model="editForm.is_superuser" />
        </el-form-item>
        <el-form-item :label="t('systemUsers.active')">
          <el-switch v-model="editForm.is_active" />
        </el-form-item>
        <el-form-item :label="t('systemUsers.groups')">
          <el-select v-model="editForm.group_ids" multiple filterable style="width: 100%">
            <el-option v-for="g in groupOptions" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="canChange" :label="t('systemUsers.password')">
          <el-input
            v-model="editForm.password"
            type="password"
            show-password
            clearable
            :placeholder="t('systemUsers.password')"
            autocomplete="new-password"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">{{ t("systemUsers.cancel") }}</el-button>
        <el-button type="primary" :loading="editSaving" @click="submitEdit">{{ t("systemUsers.save") }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import {
  createDjangoUserApi,
  listDjangoGroupsApi,
  listDjangoUsersApi,
  patchDjangoUserApi,
} from "../api";
import { useAuthStore } from "../stores/auth";

const { t } = useI18n();
const authStore = useAuthStore();

const query = reactive({ q: "" });
const items = ref([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const loading = ref(false);
const groupOptions = ref([]);

const canAdd = computed(() => authStore.hasPerm("auth.add_user"));
const canChange = computed(() => authStore.hasPerm("auth.change_user"));

const createVisible = ref(false);
const createForm = reactive({
  username: "",
  password: "",
  email: "",
  is_staff: false,
  is_superuser: false,
});
const createSaving = ref(false);

const editVisible = ref(false);
const editSaving = ref(false);
/** @type {import('vue').Ref<null | { id: number; username: string; email: string; is_staff: boolean; is_superuser: boolean; is_active: boolean; group_ids: number[]; password: string }>} */
const editForm = ref(null);

const loadGroups = async () => {
  try {
    const data = await listDjangoGroupsApi();
    groupOptions.value = data?.items || [];
  } catch {
    groupOptions.value = [];
  }
};

const load = async () => {
  loading.value = true;
  try {
    const data = await listDjangoUsersApi({
      page: page.value,
      page_size: pageSize.value,
      q: query.q || undefined,
    });
    items.value = data.items || [];
    total.value = data.pagination?.total ?? 0;
  } catch {
    ElMessage.error(t("systemUsers.loadFailed"));
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

const openDjangoAdmin = () => {
  window.open("/admin/auth/user/", "_blank", "noopener,noreferrer");
};

const resetCreate = () => {
  createForm.username = "";
  createForm.password = "";
  createForm.email = "";
  createForm.is_staff = false;
  createForm.is_superuser = false;
};

const openCreate = () => {
  resetCreate();
  createVisible.value = true;
};

const submitCreate = async () => {
  createSaving.value = true;
  try {
    await createDjangoUserApi({
      username: createForm.username,
      password: createForm.password,
      email: createForm.email || undefined,
      is_staff: createForm.is_staff,
      is_superuser: createForm.is_superuser,
    });
    ElMessage.success(t("systemUsers.createSuccess"));
    createVisible.value = false;
    await load();
  } finally {
    createSaving.value = false;
  }
};

const openEdit = (row) => {
  editForm.value = {
    id: row.id,
    username: row.username,
    email: row.email || "",
    is_staff: row.is_staff,
    is_superuser: row.is_superuser,
    is_active: row.is_active,
    group_ids: (row.groups || []).map((g) => g.id),
    password: "",
  };
  editVisible.value = true;
};

const submitEdit = async () => {
  if (!editForm.value) return;
  editSaving.value = true;
  try {
    const payload = {
      email: editForm.value.email,
      is_staff: editForm.value.is_staff,
      is_active: editForm.value.is_active,
      group_ids: editForm.value.group_ids,
    };
    if (authStore.user?.is_superuser) {
      payload.is_superuser = editForm.value.is_superuser;
    }
    if (editForm.value.password) {
      payload.password = editForm.value.password;
    }
    await patchDjangoUserApi(editForm.value.id, payload);
    ElMessage.success(t("systemUsers.updateSuccess"));
    editVisible.value = false;
    await load();
  } finally {
    editSaving.value = false;
  }
};

onMounted(async () => {
  await loadGroups();
  await load();
});
</script>

<style scoped>
.intro {
  color: var(--ip-text-secondary, #606266);
  font-size: 13px;
  margin: 0 0 8px;
}
.page-card h3 {
  margin-top: 0;
}
</style>
