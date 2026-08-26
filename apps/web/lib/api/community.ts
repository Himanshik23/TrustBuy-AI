// One function per Community Intelligence endpoint (API_DOCUMENTATION.md §4).

import { apiClient } from "./client";
import type { BadgeOut, LeaderboardEntry, ReportOut, ReportType, ReputationOut } from "@/types/community";

export async function createReport(payload: {
  report_type: ReportType;
  description: string;
  product_id?: string;
  seller_id?: string;
}): Promise<ReportOut> {
  const { data } = await apiClient.post<ReportOut>("/reports", payload);
  return data;
}

export async function listReports(params: { product_id?: string; seller_id?: string }): Promise<ReportOut[]> {
  const { data } = await apiClient.get<ReportOut[]>("/reports", { params });
  return data;
}

export async function voteReport(reportId: string, vote: 1 | -1): Promise<ReportOut> {
  const { data } = await apiClient.post<ReportOut>(`/reports/${reportId}/vote`, { vote });
  return data;
}

export async function verifyReport(reportId: string, outcome: "confirms" | "disputes", notes?: string): Promise<ReportOut> {
  const { data } = await apiClient.post<ReportOut>(`/reports/${reportId}/verify`, { outcome, notes });
  return data;
}

export async function getMyBadges(): Promise<BadgeOut[]> {
  const { data } = await apiClient.get<BadgeOut[]>("/users/me/badges");
  return data;
}

export async function getUserReputation(userId: string): Promise<ReputationOut> {
  const { data } = await apiClient.get<ReputationOut>(`/users/${userId}/reputation`);
  return data;
}

export async function getLeaderboard(): Promise<LeaderboardEntry[]> {
  const { data } = await apiClient.get<LeaderboardEntry[]>("/leaderboard");
  return data;
}
