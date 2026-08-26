// Mirrors services/community-service/app/schemas.py

export type ReportType = "fake_seller" | "counterfeit_product" | "scam" | "refund_dispute" | "genuine_confirmation";
export type ReportStatus = "pending" | "under_review" | "verified" | "rejected" | "duplicate";

export const REPORT_TYPE_LABELS: Record<ReportType, string> = {
  fake_seller: "Fake seller",
  counterfeit_product: "Counterfeit product",
  scam: "Scam",
  refund_dispute: "Refund dispute",
  genuine_confirmation: "Confirm genuine purchase",
};

export interface ReportOut {
  id: string;
  report_type: ReportType;
  description: string;
  status: ReportStatus;
  product_id: string | null;
  seller_id: string | null;
  duplicate_of_id: string | null;
  upvotes: number;
  downvotes: number;
  created_at: string;
  resolved_at: string | null;
}

export interface BadgeOut {
  code: string;
  name: string;
  description: string | null;
  icon: string | null;
}

export interface ReputationOut {
  id: string;
  display_name: string;
  trust_points: number;
  reputation_level: string;
  badges: BadgeOut[];
}

export interface LeaderboardEntry {
  id: string;
  display_name: string;
  trust_points: number;
  reputation_level: string;
}
