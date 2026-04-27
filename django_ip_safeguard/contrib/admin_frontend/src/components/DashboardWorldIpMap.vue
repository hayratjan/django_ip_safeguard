<template>
  <div ref="rootRef" class="world-ip-viz">
    <p v-if="!hasData" class="empty-tip">暂无国家/地区维度数据（需开启审计且请求带国家码）</p>
    <template v-else>
      <div ref="mapRef" class="chart map" role="img" aria-label="世界地图按国家请求量热力及攻击标点" />
      <div ref="barRef" class="chart bar" role="img" aria-label="国家请求量条形图" />
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import * as echarts from "echarts/core";
import { BarChart, MapChart, ScatterChart, EffectScatterChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  VisualMapComponent,
  TitleComponent,
  GeoComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import worldGeo from "@surbowl/world-geo-json-zh/world.zh.json";
import { useThemeStore } from "../stores/theme";

echarts.use([
  MapChart,
  BarChart,
  ScatterChart,
  EffectScatterChart,
  GridComponent,
  TooltipComponent,
  VisualMapComponent,
  TitleComponent,
  GeoComponent,
  CanvasRenderer,
]);

let worldMapRegistered = false;

const emit = defineEmits(["country-click"]);

const props = defineProps({
  distribution: { type: Array, default: () => [] },
});

const rootRef = ref(null);
const mapRef = ref(null);
const barRef = ref(null);
let mapChart;
let barChart;
let ro;

const themeStore = useThemeStore();
const isDark = computed(() => themeStore.isDark);

const ISO_ALIAS = { UK: "GB" };

const COUNTRY_NAMES = {
  CN: "中国", US: "美国", RU: "俄罗斯", JP: "日本", KR: "韩国",
  DE: "德国", FR: "法国", GB: "英国", IN: "印度", BR: "巴西",
  AU: "澳大利亚", CA: "加拿大", IT: "意大利", ES: "西班牙", NL: "荷兰",
  SG: "新加坡", HK: "中国香港", TW: "中国台湾", VN: "越南", TH: "泰国",
  ID: "印尼", MY: "马来西亚", PH: "菲律宾", UA: "乌克兰", PL: "波兰",
  TR: "土耳其", ZA: "南非", MX: "墨西哥", AR: "阿根廷", SA: "沙特",
  IR: "伊朗", IL: "以色列", SE: "瑞典", CH: "瑞士", NO: "挪威",
  FI: "芬兰", DK: "丹麦", AT: "奥地利", BE: "比利时", PT: "葡萄牙",
  IE: "爱尔兰", NZ: "新西兰", CL: "智利", CO: "哥伦比亚", PE: "秘鲁",
  EG: "埃及", NG: "尼日利亚", KE: "肯尼亚", PK: "巴基斯坦", BD: "孟加拉",
};

const COUNTRY_COORDS = {
  CN: [104.19, 35.86], US: [-95.71, 37.09], RU: [105.31, 61.52], JP: [138.25, 36.20],
  KR: [127.76, 35.90], DE: [10.45, 51.16], FR: [2.21, 46.22], GB: [-1.17, 52.35],
  IN: [78.96, 20.59], BR: [-51.92, -14.23], AU: [133.77, -25.27], CA: [-106.34, 56.13],
  IT: [12.56, 41.87], ES: [-3.74, 40.46], NL: [5.29, 52.13], SG: [103.81, 1.35],
  HK: [114.10, 22.39], TW: [120.96, 23.69], VN: [108.27, 14.05], TH: [100.99, 15.87],
  ID: [113.92, -0.78], MY: [101.97, 4.21], PH: [121.77, 12.87], UA: [31.16, 48.37],
  PL: [19.14, 51.91], TR: [35.24, 38.96], ZA: [22.93, -30.55], MX: [-102.55, 23.63],
  AR: [-63.61, -38.41], SA: [45.07, 23.88], IR: [53.68, 32.42], IL: [34.85, 31.04],
  SE: [18.64, 60.12], CH: [8.22, 46.81], NO: [8.46, 60.47], FI: [25.74, 61.92],
  DK: [9.50, 56.26], AT: [14.55, 47.51], BE: [4.46, 50.50], PT: [-8.22, 39.39],
  IE: [-8.24, 53.41], NZ: [174.88, -40.90], CL: [-71.54, -35.67], CO: [-74.29, 4.57],
  PE: [-75.01, -9.18], EG: [30.80, 26.82], NG: [10.06, 9.08], KE: [37.90, -0.02],
  PK: [69.34, 30.37], BD: [90.35, 23.68],
};

const normalizedRows = computed(() => {
  const rows = [];
  for (const item of props.distribution || []) {
    let code = String(item.country_code || "").trim().toUpperCase();
    if (!code || code === "UNKNOWN" || code === "LOCAL") continue;
    if (ISO_ALIAS[code]) code = ISO_ALIAS[code];
    const total = Number(item.count) || 0;
    const blocked = Number(item.blocked) || 0;
    const allowed = Number(item.allowed) || 0;
    if (total <= 0) continue;
    rows.push({
      code,
      count: total,
      blocked,
      allowed,
      name: item.country_name || COUNTRY_NAMES[code] || code,
    });
  }
  rows.sort((a, b) => b.count - a.count);
  return rows;
});

const hasData = computed(() => normalizedRows.value.length > 0);

function buildMapData() {
  return normalizedRows.value.map((r) => ({
    name: r.code,
    value: r.count,
    cnName: r.name,
    blocked: r.blocked,
    allowed: r.allowed,
  }));
}

function buildAttackScatterData() {
  return normalizedRows.value
    .filter((r) => r.blocked > 0 && COUNTRY_COORDS[r.code])
    .map((r) => ({
      name: r.name,
      value: [...COUNTRY_COORDS[r.code], r.blocked],
      code: r.code,
      blocked: r.blocked,
      allowed: r.allowed,
      total: r.count,
    }));
}

function disposeCharts() {
  ro?.disconnect();
  ro = null;
  mapChart?.dispose();
  barChart?.dispose();
  mapChart = null;
  barChart = null;
}

function getThemeColors() {
  const dark = isDark.value;
  return {
    titleColor: dark ? "#e5eaf3" : "#0f172a",
    subtitleColor: dark ? "#a3a6ad" : "#94a3b8",
    areaColor: dark ? "#1e293b" : "#f1f5f9",
    borderColor: dark ? "rgba(148,163,184,0.25)" : "rgba(148,163,184,0.4)",
    emphasisAreaColor: dark ? "#166534" : "#22c55e",
    emphasisBorderColor: dark ? "#4ade80" : "#fff",
    emphasisLabelColor: dark ? "#f8fafc" : "#0f172a",
    inRangeColors: dark
      ? ["#1e3a5f", "#1e6fa0", "#0ea5e9", "#38bdf8", "#7dd3fc"]
      : ["#e0f2fe", "#7dd3fc", "#0ea5e9", "#0369a1", "#0b3c5d"],
    visualMapTextColor: dark ? "#a3a6ad" : "#64748b",
    splitLineColor: dark ? "#2d3748" : "#e2e8f0",
    axisLabelColor: dark ? "#a3a6ad" : "#64748b",
    yAxisLabelColor: dark ? "#cfd3dc" : "#334155",
    tooltipBg: dark ? "rgba(30, 41, 59, 0.95)" : "rgba(15, 23, 42, 0.95)",
    tooltipText: "#f8fafc",
  };
}

function renderCharts() {
  disposeCharts();
  if (!hasData.value || !mapRef.value || !barRef.value) return;

  if (!worldMapRegistered) {
    echarts.registerMap("WorldCountry", worldGeo);
    worldMapRegistered = true;
  }

  const mapData = buildMapData();
  const attackData = buildAttackScatterData();
  const maxVal = Math.max(...mapData.map((d) => d.value), 1);
  const maxBlocked = Math.max(...attackData.map((d) => d.value[2]), 1);
  const tc = getThemeColors();

  mapChart = echarts.init(mapRef.value, null, { renderer: "canvas" });
  mapChart.setOption({
    backgroundColor: "transparent",
    title: {
      text: "全球 IP 访问与攻击分布",
      subtext: "热力=总请求 | 红点=攻击来源 | 点击查看日志",
      left: "center",
      top: 8,
      textStyle: { fontSize: 16, color: tc.titleColor, fontWeight: 700 },
      subtextStyle: { fontSize: 12, color: tc.subtitleColor },
    },
    tooltip: {
      trigger: "item",
      backgroundColor: tc.tooltipBg,
      borderColor: "transparent",
      textStyle: { color: tc.tooltipText, fontSize: 13 },
      formatter: (p) => {
        if (p.seriesType === "effectScatter" || p.seriesType === "scatter") {
          const d = p.data;
          return `<div style="font-weight:600;margin-bottom:4px">⚠ ${d.name} (${d.code})</div>` +
            `<div>总请求：<b style="color:#5eead4">${d.total}</b></div>` +
            `<div>攻击量：<b style="color:#f87171">${d.blocked}</b></div>` +
            `<div>允许量：<b style="color:#4ade80">${d.allowed}</b></div>` +
            `<div style="color:#94a3b8;font-size:11px;margin-top:4px">点击查看日志 →</div>`;
        }
        if (p.data) {
          const cn = p.data.cnName || p.name;
          const blockedInfo = p.data.blocked > 0
            ? `<div>攻击量：<b style="color:#f87171">${p.data.blocked}</b></div>` : "";
          const allowedInfo = p.data.allowed > 0
            ? `<div>允许量：<b style="color:#4ade80">${p.data.allowed}</b></div>` : "";
          return `<div style="font-weight:600;margin-bottom:4px">${cn} (${p.name})</div>` +
            `<div>总请求：<b style="color:#5eead4">${p.data.value}</b></div>` +
            blockedInfo + allowedInfo +
            `<div style="color:#94a3b8;font-size:11px;margin-top:4px">点击查看日志 →</div>`;
        }
        return p.name;
      },
    },
    visualMap: {
      min: 0,
      max: maxVal,
      text: ["多", "少"],
      realtime: true,
      calculable: true,
      orient: "vertical",
      right: 12,
      bottom: 40,
      inRange: { color: tc.inRangeColors },
      textStyle: { color: tc.visualMapTextColor },
      seriesIndex: 0,
    },
    geo: {
      map: "WorldCountry",
      roam: true,
      nameProperty: "iso_a2",
      scaleLimit: { min: 1, max: 6 },
      zoom: 1.2,
      emphasis: {
        label: { show: true, color: tc.emphasisLabelColor, fontSize: 12, fontWeight: 600 },
        itemStyle: { areaColor: tc.emphasisAreaColor, borderColor: tc.emphasisBorderColor, borderWidth: 1.5 },
      },
      itemStyle: {
        borderColor: tc.borderColor,
        borderWidth: 0.4,
        areaColor: tc.areaColor,
      },
    },
    series: [
      {
        type: "map",
        map: "WorldCountry",
        roam: false,
        nameProperty: "iso_a2",
        geoIndex: 0,
        emphasis: {
          label: { show: true, color: tc.emphasisLabelColor, fontSize: 12, fontWeight: 600 },
          itemStyle: { areaColor: tc.emphasisAreaColor, borderColor: tc.emphasisBorderColor, borderWidth: 1.5 },
        },
        select: {
          label: { show: true, color: "#fff" },
          itemStyle: { areaColor: "#0ea5e9" },
        },
        data: mapData,
      },
      {
        type: "effectScatter",
        coordinateSystem: "geo",
        data: attackData,
        symbolSize: (val) => {
          return Math.max(8, Math.min(30, (val[2] / maxBlocked) * 25 + 5));
        },
        showEffectOn: "render",
        rippleEffect: {
          brushType: "stroke",
          scale: 3,
          period: 4,
        },
        label: { show: false },
        itemStyle: {
          color: "#ef4444",
          shadowBlur: 10,
          shadowColor: "rgba(239, 68, 68, 0.5)",
        },
        zlevel: 1,
      },
    ],
  });

  mapChart.on("click", (params) => {
    if (params.data) {
      const code = params.data.code || params.name;
      if (code) emit("country-click", code);
    }
  });

  const top = normalizedRows.value.slice(0, 15);
  barChart = echarts.init(barRef.value, null, { renderer: "canvas" });
  barChart.setOption({
    backgroundColor: "transparent",
    title: {
      text: "Top 国家/地区",
      subtext: "绿色=允许 | 红色=攻击",
      left: "center",
      top: 8,
      textStyle: { fontSize: 16, color: tc.titleColor, fontWeight: 700 },
      subtextStyle: { fontSize: 12, color: tc.subtitleColor },
    },
    grid: { left: 80, right: 24, top: 56, bottom: 24 },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: tc.tooltipBg,
      borderColor: "transparent",
      textStyle: { color: tc.tooltipText },
      formatter: (params) => {
        const name = params[0]?.name || "";
        let html = `<div style="font-weight:600;margin-bottom:4px">${name}</div>`;
        for (const p of params) {
          const color = p.seriesName === "攻击" ? "#f87171" : "#4ade80";
          html += `<div>${p.seriesName}：<b style="color:${color}">${p.value}</b></div>`;
        }
        return html;
      },
    },
    xAxis: {
      type: "value",
      splitLine: { lineStyle: { type: "dashed", color: tc.splitLineColor } },
      axisLabel: { color: tc.axisLabelColor },
    },
    yAxis: {
      type: "category",
      data: top.map((r) => `${r.name} (${r.code})`).reverse(),
      axisLabel: { color: tc.yAxisLabelColor, fontSize: 12 },
    },
    series: [
      {
        name: "允许",
        type: "bar",
        stack: "total",
        data: top.map((r) => ({ value: r.allowed, code: r.code })).reverse(),
        barMaxWidth: 22,
        itemStyle: {
          borderRadius: [0, 0, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: "#4ade80" },
            { offset: 1, color: "#22c55e" },
          ]),
        },
      },
      {
        name: "攻击",
        type: "bar",
        stack: "total",
        data: top.map((r) => ({ value: r.blocked, code: r.code })).reverse(),
        barMaxWidth: 22,
        itemStyle: {
          borderRadius: [0, 6, 6, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: "#f87171" },
            { offset: 1, color: "#ef4444" },
          ]),
        },
      },
    ],
  });

  barChart.on("click", (params) => {
    if (params.data?.code) {
      emit("country-click", params.data.code);
    }
  });

  ro = new ResizeObserver(() => {
    mapChart?.resize();
    barChart?.resize();
  });
  if (rootRef.value) ro.observe(rootRef.value);
}

watch(
  [() => props.distribution, isDark],
  async () => {
    await nextTick();
    renderCharts();
  },
  { deep: true }
);

onMounted(() => renderCharts());
onUnmounted(() => disposeCharts());
</script>

<style scoped>
.world-ip-viz {
  width: 100%;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  background: var(--ip-bg-card, #fff);
  border: 1px solid var(--ip-border, #dcdfe6);
}

.empty-tip {
  margin: 0;
  padding: 48px 16px;
  text-align: center;
  color: var(--ip-text-secondary, #94a3b8);
  font-size: 14px;
  background: var(--ip-bg-card-hover, #f8fafc);
  border-radius: 8px;
  border: 1px dashed var(--ip-border, #e2e8f0);
}

.chart {
  width: 100%;
  min-height: 360px;
}

.map {
  height: 460px;
  margin-bottom: 12px;
}

.bar {
  height: 400px;
}

@media (min-width: 1100px) {
  .world-ip-viz {
    display: grid;
    grid-template-columns: 1.4fr 1fr;
    gap: 16px;
    align-items: stretch;
  }

  .map {
    margin-bottom: 0;
    min-height: 460px;
    height: 100%;
  }

  .bar {
    min-height: 460px;
    height: 100%;
  }
}
</style>
