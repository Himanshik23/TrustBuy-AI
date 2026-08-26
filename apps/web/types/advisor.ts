// Mirrors services/catalog-service/app/schemas.py Advisor* models
// (Feature: "AI Shopping Advisor & Buyer Regret Prediction").

export type BuyDecisionType =
  | "buy_now"
  | "wait_for_better_price"
  | "buy_from_different_seller"
  | "buy_with_caution"
  | "avoid_purchase"
  | "pending";

export interface BuyDecisionOut {
  decision: BuyDecisionType;
  label: string;
  explanation: string;
}

export type RegretProbability = "Very Low" | "Low" | "Medium" | "High" | "Unknown";

export interface RegretPredictionOut {
  probability: RegretProbability;
  score: number | null;
  reasons_increasing: string[];
  reasons_reducing: string[];
  ai_summary: string;
}

export interface BriefingItemOut {
  question: string;
  answer: string;
}

export interface AdvisorReportOut {
  has_data: boolean;
  buy_decision: BuyDecisionOut;
  regret_prediction: RegretPredictionOut;
  tips: string[];
  briefing: BriefingItemOut[];
  quick_questions: string[];
}

export interface AdvisorAskResponse {
  reply: string;
}

export interface AdvisorHistoryMessage {
  role: "user" | "assistant";
  content: string;
}
