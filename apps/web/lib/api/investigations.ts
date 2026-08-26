// One function per Investigation endpoint (API_DOCUMENTATION.md §2) -
// nothing outside this file calls /investigations* directly.

import { apiClient } from "./client";
import type {
  AgentRunOut,
  EvidenceItemOut,
  InvestigationCreateResponse,
  InvestigationDetail,
  InvestigationSummary,
  PriceHistoryPoint,
  SampleInvestigation,
} from "@/types/investigation";

export async function createInvestigation(url: string, forceRefresh = false): Promise<InvestigationCreateResponse> {
  const { data } = await apiClient.post<InvestigationCreateResponse>("/investigations", {
    url,
    force_refresh: forceRefresh,
  });
  return data;
}

/** Image-Based Product Analysis: a product screenshot/photo, optionally
 * alongside a URL (cross-checked against each other server-side). `url`
 * omitted or empty means image-only. */
export async function createImageInvestigation(image: File, url?: string): Promise<InvestigationCreateResponse> {
  const form = new FormData();
  form.append("image", image);
  if (url && url.trim()) form.append("url", url.trim());
  const { data } = await apiClient.post<InvestigationCreateResponse>("/investigations/image", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getInvestigation(id: string): Promise<InvestigationDetail> {
  const { data } = await apiClient.get<InvestigationDetail>(`/investigations/${id}`);
  return data;
}

export async function getEvidence(id: string): Promise<EvidenceItemOut[]> {
  const { data } = await apiClient.get<EvidenceItemOut[]>(`/investigations/${id}/evidence`);
  return data;
}

export async function getAgentRuns(id: string): Promise<AgentRunOut[]> {
  const { data } = await apiClient.get<AgentRunOut[]>(`/investigations/${id}/agents`);
  return data;
}

export async function listMyInvestigations(): Promise<InvestigationSummary[]> {
  const { data } = await apiClient.get<InvestigationSummary[]>("/users/me/investigations");
  return data;
}

export async function exportInvestigationReport(id: string): Promise<Blob> {
  const { data } = await apiClient.post<Blob>(`/investigations/${id}/report`, null, { responseType: "blob" });
  return data;
}

export async function getPriceHistory(id: string): Promise<PriceHistoryPoint[]> {
  const { data } = await apiClient.get<PriceHistoryPoint[]>(`/investigations/${id}/price-history`);
  return data;
}

export async function getSampleInvestigations(): Promise<SampleInvestigation[]> {
  const { data } = await apiClient.get<SampleInvestigation[]>("/investigations/samples");
  return data;
}
