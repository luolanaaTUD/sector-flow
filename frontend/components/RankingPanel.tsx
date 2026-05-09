"use client";

import { RankingResponse } from "@/lib/api";

interface Props {
  data: RankingResponse | undefined;
  loading?: boolean;
  onSelect?: (name: string) => void;
}

function RankRow({
  rank,
  name,
  value,
  isInflow,
  onClick,
}: {
  rank: number;
  name: string;
  value: number | null;
  isInflow: boolean;
  onClick?: () => void;
}) {
  const formatted =
    value == null
      ? "—"
      : `${value >= 0 ? "+" : ""}${value.toFixed(2)} 亿`;
  return (
    <button
      onClick={onClick}
      className="flex items-center w-full px-3 py-1.5 hover:bg-[#161b22] transition-colors text-sm gap-2 text-left"
    >
      <span className="w-4 text-zinc-600 text-xs flex-shrink-0">{rank}</span>
      <span className="flex-1 text-zinc-300 truncate">{name}</span>
      <span
        className={`flex-shrink-0 tabular-nums font-medium text-xs ${
          isInflow ? "text-red-400" : "text-green-400"
        }`}
      >
        {formatted}
      </span>
    </button>
  );
}

export default function RankingPanel({ data, loading, onSelect }: Props) {
  if (loading && !data) {
    return (
      <div className="p-3 text-xs text-zinc-600">加载排行…</div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[#0f1117] border-l border-[#2d3139]">
      <div className="p-3 border-b border-[#2d3139]">
        <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
          实时排行
        </h2>
        {data?.snapshot_ts && (
          <p className="text-[10px] text-zinc-600 mt-0.5">
            {data.snapshot_ts.replace("T", " ").slice(0, 19)}
          </p>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {data ? (
          <>
            <p className="px-3 py-1.5 text-[10px] font-semibold text-red-500 uppercase tracking-wider">
              净流入 Top
            </p>
            {data.inflow_top.map((item, i) => (
              <RankRow
                key={item.sector_name}
                rank={i + 1}
                name={item.sector_name}
                value={item.net_inflow_yi}
                isInflow={true}
                onClick={() => onSelect?.(item.sector_name)}
              />
            ))}
            <div className="border-t border-[#1c1f26] my-1" />
            <p className="px-3 py-1.5 text-[10px] font-semibold text-green-500 uppercase tracking-wider">
              净流出 Top
            </p>
            {data.outflow_top.map((item, i) => (
              <RankRow
                key={item.sector_name}
                rank={i + 1}
                name={item.sector_name}
                value={item.net_inflow_yi}
                isInflow={false}
                onClick={() => onSelect?.(item.sector_name)}
              />
            ))}
          </>
        ) : (
          <p className="p-4 text-xs text-zinc-600">暂无数据</p>
        )}
      </div>
    </div>
  );
}
