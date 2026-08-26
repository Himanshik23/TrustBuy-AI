// One function per admin endpoint (API_DOCUMENTATION.md §7).

import { apiClient } from "./client";
import type { FailedInvestigation, MetricsOverview } from "@/types/admin";
import type { ReportOut } from "@/types/community";

export async function getMetricsOverview(): Promise<MetricsOverview> {
  const { data } = await apiClient.get<MetricsOverview>("/admin/metrics/overview");
  return data;
}

export async function getFailedInvestigations(): Promise<FailedInvestigation[]> {
  const { data } = await apiClient.get<FailedInvestigation[]>("/admin/investigations/failures");
  return data;
}

export async function getModerationQueue(): Promise<ReportOut[]> {
  const { data } = await apiClient.get<ReportOut[]>("/admin/reports/queue");
  return data;
}

export async function resolveReport(reportId: string, outcome: "confirms" | "disputes"): Promise<ReportOut> {
  const { data } = await apiClient.post<ReportOut>(`/admin/reports/${reportId}/resolve`, { outcome });
  return data;
}

export async function suspendUser(userId: string): Promise<void> {
  await apiClient.post(`/admin/users/${userId}/suspend`);
}
