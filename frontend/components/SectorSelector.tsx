"use client";

import { useState, useMemo } from "react";
import { SectorInfo } from "@/lib/api";

interface Props {
  sectors: SectorInfo[];
  selected: string[];
  onToggle: (name: string) => void;
  loading?: boolean;
}

export default function SectorSelector({ sectors, selected, onToggle, loading }: Props) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(
    () =>
      sectors.filter((s) =>
        s.name.toLowerCase().includes(query.toLowerCase())
      ),
    [sectors, query]
  );

  const grouped = useMemo(() => {
    const groups: Record<string, SectorInfo[]> = { industry: [], concept: [] };
    for (const s of filtered) {
      (groups[s.type] ?? (groups[s.type] = [])).push(s);
    }
    return groups;
  }, [filtered]);

  const groupLabels: Record<string, string> = { industry: "行业", concept: "概念" };

  return (
    <div className="flex flex-col h-full bg-[#0f1117] border-r border-[#2d3139]">
      <div className="p-3 border-b border-[#2d3139]">
        <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
          板块选择
        </h2>
        <input
          type="text"
          placeholder="搜索板块…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full rounded bg-[#161b22] border border-[#2d3139] px-2 py-1.5 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-[#4a90e2] transition-colors"
        />
        {selected.length > 0 && (
          <p className="mt-1.5 text-xs text-zinc-500">
            已选 {selected.length} 个{selected.length >= 20 ? "（上限）" : ""}
          </p>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <p className="p-4 text-xs text-zinc-600">加载板块列表…</p>
        ) : (
          Object.entries(grouped).map(([type, items]) =>
            items.length === 0 ? null : (
              <div key={type}>
                <p className="sticky top-0 bg-[#0f1117] px-3 py-1.5 text-xs font-medium text-zinc-500 uppercase tracking-wider border-b border-[#1c1f26]">
                  {groupLabels[type] ?? type}
                </p>
                {items.map((s) => {
                  const active = selected.includes(s.name);
                  const atLimit = !active && selected.length >= 20;
                  return (
                    <button
                      key={s.name}
                      onClick={() => !atLimit && onToggle(s.name)}
                      disabled={atLimit}
                      className={[
                        "w-full text-left px-3 py-2 text-sm transition-colors flex items-center gap-2",
                        active
                          ? "text-white bg-[#1c2333]"
                          : atLimit
                          ? "text-zinc-700 cursor-not-allowed"
                          : "text-zinc-400 hover:bg-[#161b22] hover:text-zinc-200",
                      ].join(" ")}
                    >
                      <span
                        className={[
                          "inline-block w-3 h-3 rounded-sm border flex-shrink-0 transition-colors",
                          active
                            ? "bg-[#4a90e2] border-[#4a90e2]"
                            : "border-[#3a3f47]",
                        ].join(" ")}
                      />
                      {s.name}
                    </button>
                  );
                })}
              </div>
            )
          )
        )}
      </div>
    </div>
  );
}
