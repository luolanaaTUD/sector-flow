"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  LineSeries,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import type { IntradayResponse } from "@/lib/api";

interface Props {
  data: IntradayResponse | undefined;
  loading?: boolean;
  /** Calendar date for intraday timestamps (China session). */
  tradeDate: string;
}

const SERIES_COLORS = [
  "#e84040",
  "#f5a623",
  "#7ed321",
  "#4a90e2",
  "#9b59b6",
  "#1abc9c",
  "#e67e22",
  "#2ecc71",
  "#3498db",
  "#e74c3c",
];

function toUtcTimestamp(tradeDate: string, timeStr: string): UTCTimestamp {
  const ms = new Date(`${tradeDate}T${timeStr}+08:00`).getTime();
  return Math.floor(ms / 1000) as UTCTimestamp;
}

/** Forward-fill nulls so lines stay continuous (same idea as ECharts connectNulls). */
function buildLineData(
  tradeDate: string,
  timestamps: string[],
  values: (number | null)[]
): LineData[] {
  let carry: number | undefined;
  const out: LineData[] = [];
  for (let i = 0; i < timestamps.length; i++) {
    let v = values[i];
    if (v == null) {
      if (carry === undefined) continue;
      v = carry;
    } else {
      carry = v;
    }
    out.push({ time: toUtcTimestamp(tradeDate, timestamps[i]!), value: v });
  }
  return out;
}

function FundFlowChartInner({ data, tradeDate }: { data: IntradayResponse; tradeDate: string }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line">[]>([]);

  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;

    const chart = createChart(wrap, {
      layout: {
        background: { type: ColorType.Solid, color: "#0f1117" },
        textColor: "#c9d1d9",
        attributionLogo: true,
      },
      grid: {
        vertLines: { color: "#1f2329" },
        horzLines: { color: "#1f2329" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "#758696", width: 1, style: 2, labelBackgroundColor: "#2b2b43" },
        horzLine: { color: "#758696", width: 1, style: 2, labelBackgroundColor: "#2b2b43" },
      },
      rightPriceScale: {
        borderColor: "#2d3139",
        scaleMargins: { top: 0.08, bottom: 0.12 },
      },
      timeScale: {
        borderColor: "#2d3139",
        timeVisible: true,
        secondsVisible: false,
      },
      localization: {
        locale: "zh-CN",
        timeFormatter: (t: Time) => {
          if (typeof t === "number") {
            return new Intl.DateTimeFormat("zh-CN", {
              timeZone: "Asia/Shanghai",
              hour: "2-digit",
              minute: "2-digit",
              hour12: false,
            }).format(new Date(t * 1000));
          }
          return String(t);
        },
      },
      width: wrap.clientWidth,
      height: wrap.clientHeight,
    });

    chartRef.current = chart;

    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: wrap.clientWidth, height: wrap.clientHeight });
    });
    ro.observe(wrap);

    return () => {
      ro.disconnect();
      seriesRef.current = [];
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    for (const s of seriesRef.current) {
      chart.removeSeries(s);
    }
    seriesRef.current = [];

    const { timestamps, series } = data;
    for (let i = 0; i < series.length; i++) {
      const s = series[i]!;
      const lineData = buildLineData(tradeDate, timestamps, s.data);
      if (lineData.length === 0) continue;

      const color = SERIES_COLORS[i % SERIES_COLORS.length];
      const ser = chart.addSeries(LineSeries, {
        color,
        lineWidth: 2,
        title: s.name,
        lastValueVisible: true,
        priceLineVisible: false,
        crosshairMarkerVisible: true,
      });
      ser.setData(lineData);
      seriesRef.current.push(ser);
    }

    chart.timeScale().fitContent();
  }, [data, tradeDate]);

  return (
    <div className="flex h-full min-h-0 w-full flex-col gap-2">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-1 text-xs text-zinc-400">
        {data.series.map((s, i) => (
          <span key={s.name} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block size-2 shrink-0 rounded-full"
              style={{ backgroundColor: SERIES_COLORS[i % SERIES_COLORS.length] }}
            />
            {s.name}
          </span>
        ))}
      </div>
      <div ref={wrapRef} className="min-h-0 flex-1 w-full rounded-md border border-zinc-800/80" />
    </div>
  );
}

export default function FundFlowChart({ data, loading, tradeDate }: Props) {
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

  return <FundFlowChartInner data={data} tradeDate={tradeDate} />;
}
