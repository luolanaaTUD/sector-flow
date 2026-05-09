const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface SectorInfo {
  name: string;
  type: "industry" | "concept";
  last_updated: string | null;
}

export interface SectorSeries {
  name: string;
  data: (number | null)[];
}

export interface IntradayResponse {
  code: number;
  timestamps: string[];
  series: SectorSeries[];
}

export interface RankItem {
  sector_name: string;
  sector_type: string;
  net_inflow_yi: number | null;
  ts: string | null;
}

export interface RankingResponse {
  code: number;
  inflow_top: RankItem[];
  outflow_top: RankItem[];
  snapshot_ts: string | null;
}

export async function fetchSectors(sectorType?: string): Promise<SectorInfo[]> {
  const url = new URL(`${API_BASE}/api/sectors`);
  if (sectorType) url.searchParams.set("sector_type", sectorType);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`fetchSectors failed: ${res.status}`);
  const json = await res.json();
  return json.data as SectorInfo[];
}

export async function fetchIntraday(
  tradeDate: string,
  sectors: string[]
): Promise<IntradayResponse> {
  const res = await fetch(`${API_BASE}/api/fund_flow/intraday`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ date: tradeDate, sectors }),
  });
  if (!res.ok) throw new Error(`fetchIntraday failed: ${res.status}`);
  return res.json();
}

export async function fetchRanking(topN = 10): Promise<RankingResponse> {
  const res = await fetch(`${API_BASE}/api/fund_flow/ranking?top_n=${topN}`);
  if (!res.ok) throw new Error(`fetchRanking failed: ${res.status}`);
  return res.json();
}
