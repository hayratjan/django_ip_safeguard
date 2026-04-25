<template>
  <div class="page-card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <h2 style="margin: 0">{{ t('userChart.title') }}</h2>
      <el-select v-model="days" style="width: 140px" @change="fetchData">
        <el-option :value="3" :label="t('recentRecords.days3')" />
        <el-option :value="7" :label="t('recentRecords.days7')" />
        <el-option :value="14" :label="t('recentRecords.days14')" />
        <el-option :value="30" :label="t('recentRecords.days30')" />
      </el-select>
    </div>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="12">
        <el-card>
          <template #header>{{ t('userChart.dailyTrend') }}</template>
          <v-chart :option="dailyOption" style="height: 300px" autoresize />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>{{ t('userChart.riskDistribution') }}</template>
          <v-chart :option="riskOption" style="height: 300px" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header>{{ t('userChart.hourlyPattern') }}</template>
          <v-chart :option="hourlyOption" style="height: 300px" autoresize />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>{{ t('userChart.topCountries') }}</template>
          <v-chart :option="countryOption" style="height: 300px" autoresize />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, shallowRef } from "vue";
import { useI18n } from "vue-i18n";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, LineChart, PieChart } from "echarts/charts";
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from "echarts/components";
import { userStatsChartApi } from "../api";
import { useThemeStore } from "../stores/theme";

use([CanvasRenderer, BarChart, LineChart, PieChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent]);

const { t } = useI18n();
const themeStore = useThemeStore();

const days = ref(7);
const chartData = shallowRef({
  daily_stats: [],
  risk_distribution: [],
  top_countries: [],
  hourly_pattern: [],
});

const isDark = computed(() => themeStore.isDark);
const textColor = computed(() => (isDark.value ? "#e5eaf3" : "#303133"));
const bgColor = computed(() => (isDark.value ? "#1d1d1d" : "#ffffff"));
const splitLineColor = computed(() => (isDark.value ? "#363637" : "#e4e7ed"));
const tooltipBg = computed(() => (isDark.value ? "#2c2c2c" : "#ffffff"));
const tooltipBorder = computed(() => (isDark.value ? "#555" : "#ddd"));

const dailyOption = computed(() => {
  const data = chartData.value.daily_stats || [];
  return {
    backgroundColor: bgColor.value,
    textStyle: { color: textColor.value },
    tooltip: { trigger: "axis", backgroundColor: tooltipBg.value, borderColor: tooltipBorder.value, textStyle: { color: textColor.value } },
    legend: { data: [t("recentRecords.allow"), t("recentRecords.block")], textStyle: { color: textColor.value } },
    grid: { left: 50, right: 20, bottom: 30, top: 40 },
    xAxis: { type: "category", data: data.map((d) => d.date), axisLabel: { color: textColor.value }, splitLine: { lineStyle: { color: splitLineColor.value } } },
    yAxis: { type: "value", axisLabel: { color: textColor.value }, splitLine: { lineStyle: { color: splitLineColor.value } } },
    series: [
      { name: t("recentRecords.allow"), type: "bar", stack: "total", data: data.map((d) => d.allowed), itemStyle: { color: "#67c23a" } },
      { name: t("recentRecords.block"), type: "bar", stack: "total", data: data.map((d) => d.blocked), itemStyle: { color: "#f56c6c" } },
    ],
  };
});

const riskOption = computed(() => {
  const data = chartData.value.risk_distribution || [];
  const colorMap = { high: "#f56c6c", medium: "#e6a23c", low: "#67c23a" };
  const labelMap = { high: t("userChart.highRisk"), medium: t("userChart.mediumRisk"), low: t("userChart.lowRisk") };
  return {
    backgroundColor: bgColor.value,
    textStyle: { color: textColor.value },
    tooltip: { trigger: "item", backgroundColor: tooltipBg.value, borderColor: tooltipBorder.value, textStyle: { color: textColor.value } },
    legend: { textStyle: { color: textColor.value } },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        data: data.map((d) => ({
          name: labelMap[d.risk_level] || d.risk_level,
          value: d.count,
          itemStyle: { color: colorMap[d.risk_level] || "#409eff" },
        })),
        label: { color: textColor.value },
      },
    ],
  };
});

const hourlyOption = computed(() => {
  const data = chartData.value.hourly_pattern || [];
  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);
  const totalMap = {};
  const blockedMap = {};
  data.forEach((d) => {
    totalMap[d.hour] = d.total;
    blockedMap[d.hour] = d.blocked;
  });
  return {
    backgroundColor: bgColor.value,
    textStyle: { color: textColor.value },
    tooltip: { trigger: "axis", backgroundColor: tooltipBg.value, borderColor: tooltipBorder.value, textStyle: { color: textColor.value } },
    legend: { data: [t("recentRecords.total"), t("recentRecords.block")], textStyle: { color: textColor.value } },
    grid: { left: 50, right: 20, bottom: 30, top: 40 },
    xAxis: { type: "category", data: hours, axisLabel: { color: textColor.value }, splitLine: { lineStyle: { color: splitLineColor.value } } },
    yAxis: { type: "value", axisLabel: { color: textColor.value }, splitLine: { lineStyle: { color: splitLineColor.value } } },
    series: [
      { name: t("recentRecords.total"), type: "line", data: hours.map((_, i) => totalMap[i] || 0), smooth: true, itemStyle: { color: "#409eff" } },
      { name: t("recentRecords.block"), type: "line", data: hours.map((_, i) => blockedMap[i] || 0), smooth: true, itemStyle: { color: "#f56c6c" } },
    ],
  };
});

const countryOption = computed(() => {
  const data = chartData.value.top_countries || [];
  return {
    backgroundColor: bgColor.value,
    textStyle: { color: textColor.value },
    tooltip: { trigger: "axis", backgroundColor: tooltipBg.value, borderColor: tooltipBorder.value, textStyle: { color: textColor.value } },
    grid: { left: 80, right: 20, bottom: 30, top: 20 },
    xAxis: { type: "value", axisLabel: { color: textColor.value }, splitLine: { lineStyle: { color: splitLineColor.value } } },
    yAxis: { type: "category", data: data.map((d) => d.country_code || "—").reverse(), axisLabel: { color: textColor.value }, splitLine: { lineStyle: { color: splitLineColor.value } } },
    series: [
      { type: "bar", data: data.map((d) => d.count).reverse(), itemStyle: { color: "#409eff" } },
    ],
  };
});

async function fetchData() {
  try {
    const data = await userStatsChartApi({ days: days.value });
    chartData.value = data;
  } catch {
    // ignore
  }
}

onMounted(() => {
  fetchData();
});
</script>
