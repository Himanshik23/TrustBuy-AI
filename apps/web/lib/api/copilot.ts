// One function per Copilot endpoint (API_DOCUMENTATION.md §3).

import { apiClient } from "./client";
import type { ConversationOut, MessageResponse } from "@/types/copilot";

export async function createConversation(investigationId: string): Promise<ConversationOut> {
  const { data } = await apiClient.post<ConversationOut>("/copilot/conversations", { investigation_id: investigationId });
  return data;
}

export async function getConversation(conversationId: string): Promise<ConversationOut> {
  const { data } = await apiClient.get<ConversationOut>(`/copilot/conversations/${conversationId}`);
  return data;
}

export async function sendMessage(conversationId: string, message: string): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>(`/copilot/conversations/${conversationId}/messages`, { message });
  return data;
}
