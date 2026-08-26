"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getFailedInvestigations, getMetricsOverview, getModerationQueue, resolveReport, suspendUser } from "@/lib/api/admin";

export function useMetricsOverview(enabled: boolean) {
  return useQuery({ queryKey: ["admin", "metrics"], queryFn: getMetricsOverview, enabled });
}

export function useFailedInvestigations(enabled: boolean) {
  return useQuery({ queryKey: ["admin", "failures"], queryFn: getFailedInvestigations, enabled });
}

export function useModerationQueue(enabled: boolean) {
  return useQuery({ queryKey: ["admin", "queue"], queryFn: getModerationQueue, enabled });
}

export function useResolveReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reportId, outcome }: { reportId: string; outcome: "confirms" | "disputes" }) =>
      resolveReport(reportId, outcome),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "queue"] }),
  });
}

export function useSuspendUser() {
  return useMutation({ mutationFn: (userId: string) => suspendUser(userId) });
}
