"use client";

import dynamic from "next/dynamic";
import { useState, useCallback, useMemo, useEffect, useRef } from "react";
import SectorSelector from "@/components/SectorSelector";
import RankingPanel from "@/components/RankingPanel";
import TopBar from "@/components/TopBar";
import { useFundFlowIntraday, useRanking, useSectors } from "@/hooks/useFundFlow";
import { DEFAULT_SECTOR_NAMES } from "@/lib/defaultSectors";

// TradingView Lightweight Charts — client-only (canvas)
const FundFlowChart = dynamic(() => import("@/components/FundFlowChart"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center text-zinc-500 text-sm">
      图表加载中…
    </div>
  ),
});

const CHINA_TIME_ZONE = "Asia/Shanghai";

function getChinaNowParts() {
  const formatter = new Intl.DateTimeFormat("zh-CN", {
    timeZone: CHINA_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  const parts = formatter.formatToParts(new Date());
  const value = (type: string) => parts.find((p) => p.type === type)?.value ?? "00";
  return {
    year: Number(value("year")),
    month: Number(value("month")),
    day: Number(value("day")),
    hour: Number(value("hour")),
    minute: Number(value("minute")),
    second: Number(value("second")),
  };
}

function todayStr(): string {
  const now = getChinaNowParts();
  return `${now.year}-${String(now.month).padStart(2, "0")}-${String(now.day).padStart(2, "0")}`;
}

function isMarketOpen(): boolean {
  const now = getChinaNowParts();
  const h = now.hour;
  const m = now.minute;
  const day = new Date(`${todayStr()}T00:00:00+08:00`).getDay();
  if (day === 0 || day === 6) return false;
  const morning = (h === 9 && m >= 30) || h === 10 || (h === 11 && m <= 30);
  const afternoon = h === 13 || h === 14 || (h === 15 && m === 0);
  return morning || afternoon;
}

export default function DashboardPage() {
  const [tradeDate, setTradeDate] = useState(todayStr);
  const [selectedSectors, setSelectedSectors] = useState<string[]>([]);
  const hasAppliedDefaults = useRef(false);

  const { data: sectors, isLoading: sectorsLoading } = useSectors();
  const { data: intradayData, isLoading: intradayLoading, isValidating } =
    useFundFlowIntraday(tradeDate, selectedSectors);
  const { data: rankingData, isLoading: rankingLoading } = useRanking(10);

  useEffect(() => {
    if (hasAppliedDefaults.current || !sectors || sectors.length === 0) {
      return;
    }
    setSelectedSectors((prev) => {
      if (prev.length > 0) {
        hasAppliedDefaults.current = true;
        return prev;
      }
      const available = new Set(sectors.map((s) => s.name));
      const defaults = DEFAULT_SECTOR_NAMES.filter((name) => available.has(name)).slice(0, 20);
      hasAppliedDefaults.current = true;
      return defaults;
    });
  }, [sectors]);

  const toggleSector = useCallback((name: string) => {
    setSelectedSectors((prev) =>
      prev.includes(name) ? prev.filter((s) => s !== name) : [...prev, name]
    );
  }, []);

  const addSector = useCallback((name: string) => {
    setSelectedSectors((prev) =>
      prev.includes(name) || prev.length >= 20 ? prev : [...prev, name]
    );
  }, []);

  const lastUpdated = useMemo(() => {
    if (!intradayData) return undefined;
    return new Intl.DateTimeFormat("zh-CN", {
      timeZone: CHINA_TIME_ZONE,
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date());
  }, [intradayData]);

  return (
    <div className="flex flex-col h-screen bg-[#0f1117] text-zinc-200 overflow-hidden">
      <TopBar
        tradeDate={tradeDate}
        onDateChange={setTradeDate}
        lastUpdated={lastUpdated}
        isRefreshing={isValidating && !!intradayData}
        isMarketOpen={isMarketOpen()}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Left: sector selector */}
        <aside className="w-52 flex-shrink-0 overflow-hidden">
          <SectorSelector
            sectors={sectors ?? []}
            selected={selectedSectors}
            onToggle={toggleSector}
            loading={sectorsLoading}
          />
        </aside>

        {/* Center: chart */}
        <main className="flex-1 overflow-hidden p-3">
          <FundFlowChart
            data={intradayData}
            loading={intradayLoading}
            tradeDate={tradeDate}
          />
        </main>

        {/* Right: ranking */}
        <aside className="w-48 flex-shrink-0 overflow-hidden">
          <RankingPanel
            data={rankingData}
            loading={rankingLoading}
            onSelect={addSector}
          />
        </aside>
      </div>
    </div>
  );
}
