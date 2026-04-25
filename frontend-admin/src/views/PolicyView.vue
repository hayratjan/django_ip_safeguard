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
          placeholder="如 CN/US，仅支持两位国家码"
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
          placeholder="如 RU/KP，仅支持两位国家码"
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
      <el-divider content-position="left">中国内 / 国际 CIDR 池</el-divider>
      <p class="hint block-hint">
        池数据由远程文本（每行一条 CIDR）同步至 Redis；需先执行同步再开启「仅允许池内」，否则因无数据该规则不生效。定时任务示例：<code>0 3 * * * python manage.py sync_geo_ip_pools</code>
      </p>
      <el-form-item label="中国内网段池规则">
        <el-select v-model="form.china_pool_rule" style="width: 100%">
          <el-option label="关闭" value="off" />
          <el-option label="仅允许池内（典型：仅大陆列表内）" value="allow_only_in_pool" />
          <el-option label="池内一律拦截" value="block_in_pool" />
        </el-select>
      </el-form-item>
      <el-form-item label="国际网段池规则">
        <el-select v-model="form.international_pool_rule" style="width: 100%">
          <el-option label="关闭" value="off" />
          <el-option label="仅允许池内" value="allow_only_in_pool" />
          <el-option label="池内一律拦截" value="block_in_pool" />
        </el-select>
      </el-form-item>
      <el-form-item label="数据源 URL（只读）">
        <div class="feed-readonly">
          <div><strong>中国内</strong>：{{ form.pool_feed_urls?.geo_china_pool_url || "—" }}</div>
          <div><strong>国际</strong>：{{ form.pool_feed_urls?.geo_international_pool_url || "（未配置则不同步国际池）" }}</div>
        </div>
      </el-form-item>
      <el-form-item label="池同步状态">
        <el-table :data="poolMeta.pools" size="small" border empty-text="尚无同步记录，请先同步">
          <el-table-column prop="pool_key" label="池" width="120" />
          <el-table-column prop="line_count" label="行数" width="80" />
          <el-table-column prop="v4_interval_count" label="IPv4区间" width="100" />
          <el-table-column prop="last_ok_at" label="上次成功" min-width="160" />
          <el-table-column prop="last_error" label="错误" min-width="200" show-overflow-tooltip />
        </el-table>
        <el-button class="sync-btn" type="primary" plain :loading="syncing" :disabled="!canEditPolicy" @click="onSyncPools">
          立即同步池
        </el-button>
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
        <el-button type="primary" :loading="saving" :disabled="!canEditPolicy" @click="onSave">保存策略</el-button>
        <el-button @click="reload">重新加载</el-button>
        <span v-if="!canEditPolicy" class="hint">当前账号仅有查看权限，无法修改策略</span>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { getGeoPoolsStatusApi, getPolicyApi, syncGeoPoolsApi, updatePolicyApi } from "../api";
import { useAuthStore } from "../stores/auth";

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
    ElMessage.warning("需要策略修改权限");
    return;
  }
  syncing.value = true;
  try {
    await syncGeoPoolsApi();
    ElMessage.success("同步任务已执行");
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
      ElMessage.warning("当前账号没有策略修改权限");
      return;
    }
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
