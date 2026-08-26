"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { askAdvisor, getAdvisorReport } from "@/lib/api/advisor";
import type { AdvisorHistoryMessage } from "@/types/advisor";

export function useAdvisorReport(id: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ["investigation", id, "advisor"],
    queryFn: () => getAdvisorReport(id as string),
    enabled: Boolean(id) && enabled,
  });
}

export function useAskAdvisor(id: string | undefined) {
  return useMutation({
    mutationFn: ({ message, history }: { message: string; history?: AdvisorHistoryMessage[] }) =>
      askAdvisor(id as string, message, history),
  });
}
