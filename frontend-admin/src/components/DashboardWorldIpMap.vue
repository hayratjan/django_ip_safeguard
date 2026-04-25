<template>
  <div ref="rootRef" class="world-ip-viz">
    <p v-if="!hasData" class="empty-tip">暂无国家/地区维度数据（需开启审计且请求带国家码）</p>
    <template v-else>
      <div ref="mapRef" class="chart map" role="img" aria-label="世界地图按国家请求量热力" />
      <div ref="barRef" class="chart bar" role="img" aria-label="国家请求量条形图" />
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import * as echarts from "echarts/core";
import { BarChart, MapChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  VisualMapComponent,
  TitleComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import worldGeo from "@surbowl/world-geo-json-zh/world.zh.json";

echarts.use([
  MapChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  VisualMapComponent,
  TitleComponent,
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

const normalizedRows = computed(() => {
  const rows = [];
  for (const item of props.distribution || []) {
    let code = String(item.country_code || "").trim().toUpperCase();
    if (!code || code === "UNKNOWN") continue;
    if (ISO_ALIAS[code]) code = ISO_ALIAS[code];
    const n = Number(item.count) || 0;
    if (n <= 0) continue;
    rows.push({ code, count: n, name: COUNTRY_NAMES[code] || code });
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

function renderCharts() {
  disposeCharts();
  if (!hasData.value || !mapRef.value || !barRef.value) return;

  if (!worldMapRegistered) {
    echarts.registerMap("WorldCountry", worldGeo);
    worldMapRegistered = true;
  }

  const mapData = buildMapData();
  const maxVal = Math.max(...mapData.map((d) => d.value), 1);

  mapChart = echarts.init(mapRef.value);
  mapChart.setOption({
    title: {
      text: "全球 IP 访问热力图",
      subtext: "点击国家查看相关日志",
      left: "center",
      top: 8,
      textStyle: { fontSize: 16, color: "#0f172a", fontWeight: 700 },
      subtextStyle: { fontSize: 12, color: "#94a3b8" },
    },
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(15, 23, 42, 0.9)",
      borderColor: "transparent",
      textStyle: { color: "#f8fafc", fontSize: 13 },
      formatter: (p) => {
        if (p.data) {
          const cn = p.data.cnName || p.name;
          return `<div style="font-weight:600;margin-bottom:4px">${cn} (${p.name})</div><div>请求量：<b style="color:#5eead4">${p.data.value}</b></div><div style="color:#94a3b8;font-size:11px;margin-top:4px">点击查看日志 →</div>`;
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
      inRange: {
        color: ["#e0f2fe", "#7dd3fc", "#0ea5e9", "#0369a1", "#0b3c5d"],
      },
      textStyle: { color: "#64748b" },
    },
    series: [
      {
        type: "map",
        map: "WorldCountry",
        roam: true,
        nameProperty: "iso_a2",
        scaleLimit: { min: 0.8, max: 4 },
        emphasis: {
          label: { show: true, color: "#0f172a", fontSize: 12, fontWeight: 600 },
          itemStyle: { areaColor: "#22c55e", borderColor: "#fff", borderWidth: 1.5 },
        },
        select: {
          label: { show: true, color: "#fff" },
          itemStyle: { areaColor: "#0ea5e9" },
        },
        itemStyle: {
          borderColor: "rgba(148,163,184,0.4)",
          borderWidth: 0.4,
          areaColor: "#f1f5f9",
        },
        data: mapData,
      },
    ],
  });

  mapChart.on("click", (params) => {
    if (params.data) {
      emit("country-click", params.name);
    }
  });

  const top = normalizedRows.value.slice(0, 15);
  barChart = echarts.init(barRef.value);
  barChart.setOption({
    title: {
      text: "Top 国家/地区",
      subtext: "点击柱状图查看日志",
      left: "center",
      top: 8,
      textStyle: { fontSize: 16, color: "#0f172a", fontWeight: 700 },
      subtextStyle: { fontSize: 12, color: "#94a3b8" },
    },
    grid: { left: 80, right: 24, top: 56, bottom: 24 },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "rgba(15, 23, 42, 0.9)",
      borderColor: "transparent",
      textStyle: { color: "#f8fafc" },
    },
    xAxis: {
      type: "value",
      splitLine: { lineStyle: { type: "dashed", color: "#e2e8f0" } },
      axisLabel: { color: "#64748b" },
    },
    yAxis: {
      type: "category",
      data: top.map((r) => `${r.name} (${r.code})`).reverse(),
      axisLabel: { color: "#334155", fontSize: 12 },
    },
    series: [
      {
        type: "bar",
        data: top.map((r) => ({
          value: r.count,
          code: r.code,
        })).reverse(),
        barMaxWidth: 22,
        itemStyle: {
          borderRadius: [0, 6, 6, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: "#0ea5e9" },
            { offset: 1, color: "#0369a1" },
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
  () => props.distribution,
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
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.empty-tip {
  margin: 0;
  padding: 48px 16px;
  text-align: center;
  color: #94a3b8;
  font-size: 14px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px dashed #e2e8f0;
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
