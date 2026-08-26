"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import {
  createImageInvestigation,
  createInvestigation,
  getAgentRuns,
  getEvidence,
  getInvestigation,
  getPriceHistory,
  getSampleInvestigations,
  listMyInvestigations,
} from "@/lib/api/investigations";

export function useCreateInvestigation() {
  return useMutation({
    mutationFn: (url: string) => createInvestigation(url),
  });
}

export function useCreateImageInvestigation() {
  return useMutation({
    mutationFn: ({ image, url }: { image: File; url?: string }) => createImageInvestigation(image, url),
  });
}

/** Polls every 2s while the investigation is still processing - Phase 2's
 * documented simplification over a WebSocket stream (ADR-011's transport
 * tradeoff applies to the client too, not just the backend queue).
 * `refetchIntervalInBackground: true` because a user switching tabs while
 * their investigation runs should still see it finished when they come
 * back, not a stale "processing" snapshot from before they tabbed away. */
export function useInvestigation(id: string | undefined) {
  return useQuery({
    queryKey: ["investigation", id],
    queryFn: () => getInvestigation(id as string),
    enabled: Boolean(id),
    refetchInterval: (query) => (query.state.data?.status === "processing" ? 2000 : false),
    refetchIntervalInBackground: true,
  });
}

export function useEvidence(id: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ["investigation", id, "evidence"],
    queryFn: () => getEvidence(id as string),
    enabled: Boolean(id) && enabled,
  });
}

export function useAgentRuns(id: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ["investigation", id, "agents"],
    queryFn: () => getAgentRuns(id as string),
    enabled: Boolean(id) && enabled,
  });
}

export function usePriceHistory(id: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ["investigation", id, "price-history"],
    queryFn: () => getPriceHistory(id as string),
    enabled: Boolean(id) && enabled,
  });
}

/** Public - powers the landing page's "Try a sample" links. Static-ish
 * data (already-completed investigations), so a longer staleTime avoids
 * re-fetching on every landing page visit. */
export function useSampleInvestigations() {
  return useQuery({
    queryKey: ["sample-investigations"],
    queryFn: getSampleInvestigations,
    staleTime: 5 * 60 * 1000,
  });
}

export function useMyInvestigations(enabled: boolean) {
  return useQuery({
    queryKey: ["my-investigations"],
    queryFn: listMyInvestigations,
    enabled,
  });
}
