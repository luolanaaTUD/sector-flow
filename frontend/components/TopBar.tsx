"use client";

interface Props {
  tradeDate: string;
  onDateChange: (d: string) => void;
  lastUpdated?: string;
  isRefreshing?: boolean;
  isMarketOpen?: boolean;
}

export default function TopBar({
  tradeDate,
  onDateChange,
  lastUpdated,
  isRefreshing,
  isMarketOpen,
}: Props) {
  return (
    <header className="flex items-center justify-between px-4 py-2 bg-[#0f1117] border-b border-[#2d3139] h-12 flex-shrink-0">
      <div className="flex items-center gap-3">
        <span className="text-white font-semibold text-sm tracking-wide">
          A股板块资金流向
        </span>
        <span
          className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
            isMarketOpen
              ? "bg-green-900/60 text-green-400"
              : "bg-zinc-800 text-zinc-500"
          }`}
        >
          {isMarketOpen ? "盘中" : "收盘"}
        </span>
      </div>

      <div className="flex items-center gap-4">
        {lastUpdated && (
          <span className="text-[11px] text-zinc-500">
            {isRefreshing ? "刷新中…" : `更新 ${lastUpdated}`}
          </span>
        )}
        <input
          type="date"
          value={tradeDate}
          onChange={(e) => onDateChange(e.target.value)}
          className="rounded bg-[#161b22] border border-[#2d3139] px-2 py-1 text-xs text-zinc-300 focus:outline-none focus:border-[#4a90e2] transition-colors"
        />
      </div>
    </header>
  );
}
