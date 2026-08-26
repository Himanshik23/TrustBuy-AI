"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createReport,
  getLeaderboard,
  getMyBadges,
  getUserReputation,
  listReports,
  verifyReport,
  voteReport,
} from "@/lib/api/community";
import type { ReportType } from "@/types/community";

export function useReports(params: { product_id?: string; seller_id?: string }) {
  return useQuery({
    queryKey: ["reports", params],
    queryFn: () => listReports(params),
    enabled: Boolean(params.product_id || params.seller_id),
  });
}

export function useCreateReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { report_type: ReportType; description: string; product_id?: string; seller_id?: string }) =>
      createReport(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports"] }),
  });
}

export function useVoteReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reportId, vote }: { reportId: string; vote: 1 | -1 }) => voteReport(reportId, vote),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports"] }),
  });
}

export function useVerifyReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reportId, outcome }: { reportId: string; outcome: "confirms" | "disputes" }) =>
      verifyReport(reportId, outcome),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports"] }),
  });
}

export function useMyBadges(enabled: boolean) {
  return useQuery({ queryKey: ["my-badges"], queryFn: getMyBadges, enabled });
}

export function useUserReputation(userId: string | undefined) {
  return useQuery({
    queryKey: ["reputation", userId],
    queryFn: () => getUserReputation(userId as string),
    enabled: Boolean(userId),
  });
}

export function useLeaderboard() {
  return useQuery({ queryKey: ["leaderboard"], queryFn: getLeaderboard });
}
