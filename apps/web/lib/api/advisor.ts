// One function per Advisor endpoint (Feature: "AI Shopping Advisor & Buyer
// Regret Prediction") - nothing outside this file calls /advisor* directly.

import { apiClient } from "./client";
import type { AdvisorAskResponse, AdvisorHistoryMessage, AdvisorReportOut } from "@/types/advisor";

export async function getAdvisorReport(investigationId: string): Promise<AdvisorReportOut> {
  const { data } = await apiClient.get<AdvisorReportOut>(`/investigations/${investigationId}/advisor`);
  return data;
}

export async function askAdvisor(
  investigationId: string,
  message: string,
  history: AdvisorHistoryMessage[] = []
): Promise<AdvisorAskResponse> {
  const { data } = await apiClient.post<AdvisorAskResponse>(`/investigations/${investigationId}/advisor/ask`, {
    message,
    history,
  });
  return data;
}
