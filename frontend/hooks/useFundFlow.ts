"use client";

import useSWR from "swr";
import { fetchIntraday, fetchRanking, fetchSectors, IntradayResponse, RankingResponse, SectorInfo } from "@/lib/api";

const REFRESH_INTERVAL_MS = 60_000;

export function useSectors(sectorType?: string) {
  return useSWR<SectorInfo[]>(
    ["sectors", sectorType],
    () => fetchSectors(sectorType),
    { refreshInterval: REFRESH_INTERVAL_MS, revalidateOnFocus: false }
  );
}

export function useFundFlowIntraday(tradeDate: string, sectors: string[]) {
  const enabled = sectors.length > 0;
  return useSWR<IntradayResponse>(
    enabled ? ["intraday", tradeDate, ...sectors] : null,
    () => fetchIntraday(tradeDate, sectors),
    {
      refreshInterval: REFRESH_INTERVAL_MS,
      revalidateOnFocus: false,
      keepPreviousData: true,
    }
  );
}

export function useRanking(topN = 10) {
  return useSWR<RankingResponse>(
    ["ranking", topN],
    () => fetchRanking(topN),
    { refreshInterval: REFRESH_INTERVAL_MS, revalidateOnFocus: false }
  );
}
