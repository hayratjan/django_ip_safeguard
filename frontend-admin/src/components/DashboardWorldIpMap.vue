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

const props = defineProps({
  /** 与接口一致：{ country_code, count }[] */
  distribution: { type: Array, default: () => [] },
});

const rootRef = ref(null);
const mapRef = ref(null);
const barRef = ref(null);
let mapChart;
let barChart;
let ro;

// 常见国家码别名，便于与 GeoJSON 中 iso_a2 对齐
const ISO_ALIAS = { UK: "GB" };

const normalizedRows = computed(() => {
  const rows = [];
  for (const item of props.distribution || []) {
    let code = String(item.country_code || "").trim().toUpperCase();
    if (!code || code === "UNKNOWN") {
      continue;
    }
    if (ISO_ALIAS[code]) {
      code = ISO_ALIAS[code];
    }
    const n = Number(item.count) || 0;
    if (n <= 0) {
      continue;
    }
    rows.push({ code, count: n, name: code });
  }
  rows.sort((a, b) => b.count - a.count);
  return rows;
});

const hasData = computed(() => normalizedRows.value.length > 0);

function buildMapData() {
  return normalizedRows.value.map((r) => ({ name: r.code, value: r.count }));
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
  if (!hasData.value || !mapRef.value || !barRef.value) {
    return;
  }

  if (!worldMapRegistered) {
    echarts.registerMap("WorldCountry", worldGeo);
    worldMapRegistered = true;
  }

  const mapData = buildMapData();
  const maxVal = Math.max(...mapData.map((d) => d.value), 1);

  mapChart = echarts.init(mapRef.value);
  mapChart.setOption({
    title: {
      text: "世界地图 · 请求量热力",
      left: "center",
      top: 8,
      textStyle: { fontSize: 14, color: "#334155", fontWeight: 600 },
    },
    tooltip: {
      trigger: "item",
      formatter: (p) => {
        if (p.data) {
          return `${p.name}<br/>请求量：<b>${p.data.value}</b>`;
        }
        return `${p.name}`;
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
        color: ["#e0f2fe", "#5eead4", "#0f766e", "#0b3c5d"],
      },
    },
    series: [
      {
        type: "map",
        map: "WorldCountry",
        roam: true,
        nameProperty: "iso_a2",
        scaleLimit: { min: 0.8, max: 4 },
        emphasis: {
          label: { show: true, color: "#0f172a", fontSize: 11 },
          itemStyle: { areaColor: "#22c55e", borderColor: "#fff", borderWidth: 1 },
        },
        itemStyle: {
          borderColor: "rgba(148,163,184,0.6)",
          borderWidth: 0.4,
          areaColor: "#f1f5f9",
        },
        data: mapData,
      },
    ],
  });

  const top = normalizedRows.value.slice(0, 15);
  barChart = echarts.init(barRef.value);
  barChart.setOption({
    title: {
      text: "Top 国家/地区",
      left: "center",
      top: 8,
      textStyle: { fontSize: 14, color: "#334155", fontWeight: 600 },
    },
    grid: { left: 72, right: 24, top: 48, bottom: 24 },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: { type: "value", splitLine: { lineStyle: { type: "dashed" } } },
    yAxis: {
      type: "category",
      data: top.map((r) => r.code).reverse(),
      axisLabel: { color: "#64748b" },
    },
    series: [
      {
        type: "bar",
        data: top.map((r) => r.count).reverse(),
        barMaxWidth: 22,
        itemStyle: {
          borderRadius: [0, 4, 4, 0],
          color: "#0f766e",
        },
      },
    ],
  });

  ro = new ResizeObserver(() => {
    mapChart?.resize();
    barChart?.resize();
  });
  if (rootRef.value) {
    ro.observe(rootRef.value);
  }
}

watch(
  () => props.distribution,
  async () => {
    await nextTick();
    renderCharts();
  },
  { deep: true }
);

onMounted(() => {
  renderCharts();
});

onUnmounted(() => {
  disposeCharts();
});
</script>

<style scoped>
.world-ip-viz {
  width: 100%;
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
  height: 420px;
  margin-bottom: 12px;
}

.bar {
  height: 380px;
}

@media (min-width: 1100px) {
  .world-ip-viz {
    display: grid;
    grid-template-columns: 1.35fr 1fr;
    gap: 16px;
    align-items: stretch;
  }

  .map {
    margin-bottom: 0;
    min-height: 420px;
    height: 100%;
  }

  .bar {
    min-height: 420px;
    height: 100%;
  }
}
</style>
