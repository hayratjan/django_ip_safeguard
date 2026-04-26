<template>
  <div class="page-card">
    <div class="page-header">
      <h2>{{ t('scheduledTasks.title') }}</h2>
      <div class="header-actions">
        <el-button type="primary" @click="onAddTask">
          {{ t('scheduledTasks.addTask') }}
        </el-button>
        <el-button @click="loadTasks">
          {{ t('common.refresh') }}
        </el-button>
      </div>
    </div>

    <el-card shadow="never">
      <el-form :inline="true" class="filter-form">
        <el-form-item :label="t('scheduledTasks.taskType')">
          <el-select v-model="filters.task_type" clearable @change="loadTasks">
            <el-option value="" :label="t('common.all')" />
            <el-option value="geoip2_update" :label="t('scheduledTasks.geoip2Update')" />
            <el-option value="threat_intel_sync" :label="t('scheduledTasks.threatIntelSync')" />
            <el-option value="ip_reputation_snapshot" :label="t('scheduledTasks.ipReputationSnapshot')" />
            <el-option value="geo_pool_sync" :label="t('scheduledTasks.geoPoolSync')" />
            <el-option value="custom" :label="t('scheduledTasks.custom')" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('scheduledTasks.enabled')">
          <el-select v-model="filters.enabled" clearable @change="loadTasks">
            <el-option value="" :label="t('common.all')" />
            <el-option value="true" :label="t('common.yes')" />
            <el-option value="false" :label="t('common.no')" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-table :data="tasks" v-loading="loading" stripe>
        <el-table-column prop="name" :label="t('scheduledTasks.taskName')" min-width="150" />
        <el-table-column :label="t('scheduledTasks.taskType')" width="160">
          <template #default="{ row }">
            {{ row.task_type_display }}
          </template>
        </el-table-column>
        <el-table-column :label="t('scheduledTasks.schedule')" width="180">
          <template #default="{ row }">
            <span>{{ row.schedule_display }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('scheduledTasks.status')" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.enabled" type="success" size="small">{{ t('common.enabled') }}</el-tag>
            <el-tag v-else type="info" size="small">{{ t('common.disabled') }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('scheduledTasks.lastRun')" width="160">
          <template #default="{ row }">
            <span v-if="row.last_run_at">{{ formatDateTime(row.last_run_at) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('scheduledTasks.nextRun')" width="160">
          <template #default="{ row }">
            <span v-if="row.next_run_at">{{ formatDateTime(row.next_run_at) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('scheduledTasks.runCount')" width="100">
          <template #default="{ row }">
            <span>{{ row.success_count }}/{{ row.run_count }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('common.actions')" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="onRunTask(row)">
              {{ t('scheduledTasks.runNow') }}
            </el-button>
            <el-button size="small" type="primary" link @click="onEditTask(row)">
              {{ t('common.edit') }}
            </el-button>
            <el-button size="small" type="danger" link @click="onDeleteTask(row)">
              {{ t('common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @current-change="loadTasks"
          @size-change="loadTasks"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'add' ? t('scheduledTasks.addTask') : t('scheduledTasks.editTask')"
      width="600px"
    >
      <el-form ref="formRef" :model="taskForm" :rules="formRules" label-width="140px">
        <el-form-item :label="t('scheduledTasks.taskName')" prop="name">
          <el-input v-model="taskForm.name" :placeholder="t('scheduledTasks.taskNamePlaceholder')" :disabled="dialogMode === 'edit'" />
        </el-form-item>
        <el-form-item :label="t('scheduledTasks.taskType')" prop="task_type">
          <el-select v-model="taskForm.task_type" @change="onTaskTypeChange">
            <el-option value="geoip2_update" :label="t('scheduledTasks.geoip2Update')" />
            <el-option value="threat_intel_sync" :label="t('scheduledTasks.threatIntelSync')" />
            <el-option value="ip_reputation_snapshot" :label="t('scheduledTasks.ipReputationSnapshot')" />
            <el-option value="geo_pool_sync" :label="t('scheduledTasks.geoPoolSync')" />
            <el-option value="custom" :label="t('scheduledTasks.custom')" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('scheduledTasks.scheduleType')">
          <el-radio-group v-model="scheduleType" @change="onScheduleTypeChange">
            <el-radio value="preset">{{ t('scheduledTasks.usePreset') }}</el-radio>
            <el-radio value="interval">{{ t('scheduledTasks.useInterval') }}</el-radio>
            <el-radio value="cron">{{ t('scheduledTasks.useCron') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="scheduleType === 'preset'" :label="t('scheduledTasks.cronPreset')" prop="cron_preset">
          <el-select v-model="taskForm.cron_preset">
            <el-option value="@hourly" :label="t('scheduledTasks.hourly')" />
            <el-option value="@daily" :label="t('scheduledTasks.daily')" />
            <el-option value="@weekly" :label="t('scheduledTasks.weekly')" />
            <el-option value="@monthly" :label="t('scheduledTasks.monthly')" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="scheduleType === 'interval'" :label="t('scheduledTasks.intervalMinutes')" prop="interval_minutes">
          <el-input-number v-model="taskForm.interval_minutes" :min="1" :max="10080" />
        </el-form-item>
        <el-form-item v-if="scheduleType === 'cron'" :label="t('scheduledTasks.cronExpression')" prop="cron_expression">
          <el-input v-model="taskForm.cron_expression" placeholder="0 3 * * *" />
          <div class="form-help">{{ t('scheduledTasks.cronHelp') }}</div>
        </el-form-item>
        <el-form-item v-if="taskForm.task_type === 'custom'" :label="t('scheduledTasks.command')" prop="command">
          <el-input v-model="taskForm.command" placeholder="update_geoip2_db --force" />
        </el-form-item>
        <el-form-item :label="t('scheduledTasks.enabled')">
          <el-switch v-model="taskForm.enabled" />
        </el-form-item>
        <el-form-item :label="t('scheduledTasks.description')">
          <el-input v-model="taskForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="saveLoading" @click="onSaveTask">
          {{ t('common.save') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { ElMessage, ElMessageBox } from "element-plus";
import { getScheduledTaskListApi, createScheduledTaskApi, getScheduledTaskDetailApi, updateScheduledTaskApi, deleteScheduledTaskApi, runScheduledTaskApi } from "../api";
import { formatDateTime } from "../utils/time";

const { t } = useI18n();

const loading = ref(false);
const saveLoading = ref(false);
const tasks = ref([]);
const dialogVisible = ref(false);
const dialogMode = ref("add");
const editingTaskId = ref(null);
const formRef = ref(null);

const scheduleType = ref("preset");

const filters = reactive({
  task_type: "",
  enabled: "",
});

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
});

const taskForm = reactive({
  name: "",
  task_type: "geoip2_update",
  cron_preset: "@daily",
  cron_expression: "",
  interval_minutes: 0,
  enabled: true,
  description: "",
  command: "",
});

const formRules = {
  name: [{ required: true, message: t("scheduledTasks.taskNameRequired"), trigger: "blur" }],
  task_type: [{ required: true, message: t("scheduledTasks.taskTypeRequired"), trigger: "change" }],
};

const onTaskTypeChange = () => {
  if (taskForm.task_type !== "custom") {
    taskForm.command = "";
  }
};

const onScheduleTypeChange = () => {
  if (scheduleType.value === "preset") {
    taskForm.interval_minutes = 0;
    taskForm.cron_expression = "";
  } else if (scheduleType.value === "interval") {
    taskForm.cron_preset = "@daily";
    taskForm.cron_expression = "";
  } else if (scheduleType.value === "cron") {
    taskForm.cron_preset = "@daily";
    taskForm.interval_minutes = 0;
  }
};

const loadTasks = async () => {
  loading.value = true;
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
    };
    if (filters.task_type) params.task_type = filters.task_type;
    if (filters.enabled) params.enabled = filters.enabled;

    const res = await getScheduledTaskListApi(params);
    tasks.value = res.items || [];
    pagination.total = res.pagination?.total || 0;
  } catch (err) {
    ElMessage.error(err.message || t("common.loadFailed"));
  } finally {
    loading.value = false;
  }
};

const onAddTask = () => {
  dialogMode.value = "add";
  editingTaskId.value = null;
  resetForm();
  scheduleType.value = "preset";
  taskForm.cron_preset = "@daily";
  dialogVisible.value = true;
};

const onEditTask = async (row) => {
  dialogMode.value = "edit";
  editingTaskId.value = row.id;
  try {
    const res = await getScheduledTaskDetailApi(row.id);
    const data = res.data;
    taskForm.name = data.name;
    taskForm.task_type = data.task_type;
    taskForm.cron_preset = data.cron_preset;
    taskForm.cron_expression = data.cron_expression;
    taskForm.interval_minutes = data.interval_minutes;
    taskForm.enabled = data.enabled;
    taskForm.description = data.description;
    taskForm.command = data.command;

    if (data.interval_minutes > 0) {
      scheduleType.value = "interval";
    } else if (data.cron_expression) {
      scheduleType.value = "cron";
    } else {
      scheduleType.value = "preset";
    }

    dialogVisible.value = true;
  } catch (err) {
    ElMessage.error(err.message || t("common.loadFailed"));
  }
};

const onSaveTask = async () => {
  if (!formRef.value) return;
  try {
    await formRef.value.validate();
  } catch {
    return;
  }

  saveLoading.value = true;
  try {
    const payload = { ...taskForm };
    if (scheduleType.value === "preset") {
      payload.interval_minutes = 0;
      payload.cron_expression = "";
    } else if (scheduleType.value === "interval") {
      payload.cron_preset = "@daily";
      payload.cron_expression = "";
    } else if (scheduleType.value === "cron") {
      payload.cron_preset = "@daily";
      payload.interval_minutes = 0;
    }

    if (dialogMode.value === "add") {
      await createScheduledTaskApi(payload);
      ElMessage.success(t("scheduledTasks.createSuccess"));
    } else {
      await updateScheduledTaskApi(editingTaskId.value, payload);
      ElMessage.success(t("scheduledTasks.updateSuccess"));
    }
    dialogVisible.value = false;
    loadTasks();
  } catch (err) {
    ElMessage.error(err.message || t("common.saveFailed"));
  } finally {
    saveLoading.value = false;
  }
};

const onDeleteTask = async (row) => {
  try {
    await ElMessageBox.confirm(
      t("scheduledTasks.deleteConfirm", { name: row.name }),
      t("common.confirm"),
      { type: "warning" }
    );
    await deleteScheduledTaskApi(row.id);
    ElMessage.success(t("scheduledTasks.deleteSuccess"));
    loadTasks();
  } catch (err) {
    if (err !== "cancel") {
      ElMessage.error(err.message || t("common.deleteFailed"));
    }
  }
};

const onRunTask = async (row) => {
  try {
    await ElMessageBox.confirm(
      t("scheduledTasks.runConfirm", { name: row.name }),
      t("common.confirm"),
      { type: "info" }
    );
    await runScheduledTaskApi(row.id);
    ElMessage.success(t("scheduledTasks.runTriggered"));
    loadTasks();
  } catch (err) {
    if (err !== "cancel") {
      ElMessage.error(err.message || t("common操作失败"));
    }
  }
};

const resetForm = () => {
  taskForm.name = "";
  taskForm.task_type = "geoip2_update";
  taskForm.cron_preset = "@daily";
  taskForm.cron_expression = "";
  taskForm.interval_minutes = 0;
  taskForm.enabled = true;
  taskForm.description = "";
  taskForm.command = "";
};

onMounted(() => {
  loadTasks();
});
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.filter-form {
  margin-bottom: 16px;
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.text-muted {
  color: #999;
}

.form-help {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}
</style>
