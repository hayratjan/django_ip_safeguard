<template>
  <div class="page-card">
    <h3>策略中心</h3>
    <el-form :model="form" label-width="180px">
      <el-form-item label="启用防护"><el-switch v-model="form.enabled" /></el-form-item>
      <el-form-item label="风险阈值"><el-input-number v-model="form.risk_score_threshold" :min="0" :max="100" /></el-form-item>
      <el-form-item label="风险标签黑名单">
        <el-select
          v-model="form.blocked_risk_tags"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="输入后回车添加"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="国家白名单">
        <el-select
          v-model="form.allowed_countries"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="如 CN"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="国家黑名单">
        <el-select
          v-model="form.blocked_countries"
          multiple
          filterable
          allow-create
          default-first-option
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="IP 白名单">
        <el-select
          v-model="form.ip_whitelist"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="单 IP 或 CIDR，如 203.0.113.5 或 10.0.0.0/8"
          style="width: 100%"
        />
        <span class="hint">命中白名单的请求直接放行，不查情报、不计入黑名单与限流</span>
      </el-form-item>
      <el-form-item label="IP 黑名单">
        <el-select
          v-model="form.ip_blacklist"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="单 IP 或 CIDR，如 198.51.100.0/24"
          style="width: 100%"
        />
        <span class="hint">在白名单之后、情报之前拦截；不自动写入封禁键</span>
      </el-form-item>
      <el-form-item label="单 IP 每分钟请求上限">
        <el-input-number v-model="form.rate_limit_per_minute" :min="0" :max="100000" />
        <span class="hint">0 关闭；启用后同一 IP 在 60 秒滑动窗口内超过该次数则拦截（Redis 计数）</span>
      </el-form-item>
      <el-form-item label="全局失败放行"><el-switch v-model="form.fail_open" /></el-form-item>
      <el-form-item label="按路径失败放行前缀">
        <el-select
          v-model="form.fail_open_path_prefixes"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="如 /api/health/"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="按路径失败阻断前缀">
        <el-select
          v-model="form.fail_close_path_prefixes"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="如 /admin/ /api/pay/"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="拦截状态码"><el-input-number v-model="form.block_status_code" :min="400" :max="499" /></el-form-item>
      <el-form-item label="情报缓存 TTL（秒）"><el-input-number v-model="form.cache_ttl" :min="60" /></el-form-item>
      <el-form-item label="封禁 TTL（秒）"><el-input-number v-model="form.ban_ttl" :min="60" /></el-form-item>
      <el-form-item label="写入数据库审计">
        <el-switch v-model="form.use_db_log" />
        <span class="hint">开启后拦截/放行会写库，流量大时请评估性能</span>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="saving" @click="onSave">保存策略</el-button>
        <el-button @click="reload">重新加载</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { getPolicyApi, updatePolicyApi } from "../api";

// 与后端 IpGuardPolicy 字段对齐的默认值，避免控件读到 undefined
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
});

const form = reactive(emptyForm());
const saving = ref(false);

const reload = async () => {
  Object.assign(form, emptyForm(), await getPolicyApi());
};

onMounted(reload);

const onSave = async () => {
  saving.value = true;
  try {
    await updatePolicyApi({ ...form });
    ElMessage.success("策略已保存");
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
</style>
