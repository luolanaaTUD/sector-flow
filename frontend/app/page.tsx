"use client";

import dynamic from "next/dynamic";
import { useState, useCallback, useMemo } from "react";
import SectorSelector from "@/components/SectorSelector";
import RankingPanel from "@/components/RankingPanel";
import TopBar from "@/components/TopBar";
import { useFundFlowIntraday, useRanking, useSectors } from "@/hooks/useFundFlow";

// ECharts is heavy – load on client only
const FundFlowChart = dynamic(() => import("@/components/FundFlowChart"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center text-zinc-500 text-sm">
      图表加载中…
    </div>
  ),
});

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

function isMarketOpen(): boolean {
  const now = new Date();
  const h = now.getHours();
  const m = now.getMinutes();
  const day = now.getDay();
  if (day === 0 || day === 6) return false;
  const morning = (h === 9 && m >= 30) || h === 10 || (h === 11 && m <= 30);
  const afternoon = h === 13 || h === 14 || (h === 15 && m === 0);
  return morning || afternoon;
}

export default function DashboardPage() {
  const [tradeDate, setTradeDate] = useState(todayStr);
  const [selectedSectors, setSelectedSectors] = useState<string[]>([]);

  const { data: sectors, isLoading: sectorsLoading } = useSectors();
  const { data: intradayData, isLoading: intradayLoading, isValidating } =
    useFundFlowIntraday(tradeDate, selectedSectors);
  const { data: rankingData, isLoading: rankingLoading } = useRanking(10);

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
    return new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
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
          <FundFlowChart data={intradayData} loading={intradayLoading} />
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
