"use client";

import ReactECharts from "echarts-for-react";
import type { EChartsOption, LineSeriesOption } from "echarts";
import { IntradayResponse } from "@/lib/api";

interface Props {
  data: IntradayResponse | undefined;
  loading?: boolean;
}

const INFLOW_COLORS = [
  "#e84040", "#f5a623", "#7ed321", "#4a90e2", "#9b59b6",
  "#1abc9c", "#e67e22", "#2ecc71", "#3498db", "#e74c3c",
];

function buildOption(data: IntradayResponse): EChartsOption {
  const { timestamps, series } = data;

  const seriesDefs: LineSeriesOption[] = series.map((s, i) => {
    const lastVal = [...s.data].reverse().find((v) => v !== null);
    const isInflow = lastVal !== undefined && lastVal >= 0;

    return {
      name: s.name,
      type: "line",
      smooth: true,
      symbol: "none",
      data: s.data,
      lineStyle: { width: 2 },
      color: INFLOW_COLORS[i % INFLOW_COLORS.length],
      endLabel: {
        show: true,
        formatter: "{a}",
        color: isInflow ? "#e84040" : "#27ae60",
        fontWeight: "bold",
        fontSize: 11,
      },
      connectNulls: false,
    };
  });

  return {
    backgroundColor: "#0f1117",
    textStyle: { color: "#c9d1d9" },
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "cross",
        crossStyle: { color: "#666" },
        lineStyle: { color: "#666", type: "dashed" },
      },
      backgroundColor: "#1c1f26",
      borderColor: "#2d3139",
      textStyle: { color: "#c9d1d9" },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      formatter: (params: any) => {
        const items = params as Array<{
          seriesName: string;
          value: number | null;
          color: string;
          name: string;
        }>;
        if (!items.length) return "";
        const time = items[0].name;
        const lines = items.map((p) => {
          const val = p.value == null ? "—" : `${p.value >= 0 ? "+" : ""}${p.value.toFixed(2)} 亿`;
          const color = p.value != null && p.value >= 0 ? "#e84040" : "#27ae60";
          return `<span style="color:${p.color}">●</span> ${p.seriesName}: <b style="color:${color}">${val}</b>`;
        });
        return `<div style="font-size:12px"><b>${time}</b><br/>${lines.join("<br/>")}</div>`;
      },
    },
    legend: {
      top: 8,
      right: 8,
      textStyle: { color: "#c9d1d9", fontSize: 12 },
      icon: "circle",
      itemWidth: 10,
      itemHeight: 10,
    },
    grid: { left: 60, right: 140, top: 48, bottom: 64 },
    xAxis: {
      type: "category",
      data: timestamps,
      axisLine: { lineStyle: { color: "#2d3139" } },
      axisTick: { show: false },
      axisLabel: {
        color: "#7d8590",
        fontSize: 11,
        interval: 29,
        formatter: (val: string) => val.slice(0, 5),
      },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      name: "净流入 (亿元)",
      nameTextStyle: { color: "#7d8590", fontSize: 11, padding: [0, 0, 0, 40] },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: "#7d8590",
        fontSize: 11,
        formatter: (val: number) => (val >= 0 ? `+${val}` : `${val}`),
      },
      splitLine: { lineStyle: { color: "#1f2329", type: "dashed" } },
    },
    dataZoom: [
      {
        type: "slider",
        bottom: 8,
        height: 20,
        fillerColor: "rgba(100,110,130,0.2)",
        borderColor: "#2d3139",
        textStyle: { color: "#7d8590" },
        handleStyle: { color: "#4a90e2" },
      },
      { type: "inside", throttle: 50 },
    ],
    series: seriesDefs,
  };
}

export default function FundFlowChart({ data, loading }: Props) {
  if (loading && !data) {
    return (
      <div className="flex h-full items-center justify-center text-zinc-500 text-sm">
        加载中…
      </div>
    );
  }
  if (!data || data.series.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-zinc-500 text-sm">
        请在左侧选择板块
      </div>
    );
  }

  return (
    <ReactECharts
      option={buildOption(data)}
      style={{ height: "100%", width: "100%" }}
      opts={{ renderer: "canvas" }}
      notMerge={false}
      lazyUpdate={true}
    />
  );
}
