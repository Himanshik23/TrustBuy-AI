// Mirrors services/catalog-service/app/schemas.py copilot models.

export interface CopilotMessageOut {
  role: "user" | "assistant";
  content: string;
  cited_evidence_ids: string[];
  created_at: string;
}

export interface ConversationOut {
  id: string;
  investigation_id: string;
  messages: CopilotMessageOut[];
}

export interface MessageResponse {
  reply: string;
  cited_evidence_ids: string[];
  intent_matched: string;
  suggested_followups: string[];
}

export const SUGGESTED_QUESTIONS = [
  "Why did you recommend this verdict?",
  "Which reviews look fake?",
  "Show stronger evidence.",
  "Should I wait before buying?",
];
