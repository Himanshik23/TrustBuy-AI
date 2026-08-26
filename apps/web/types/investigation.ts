// Mirrors services/catalog-service/app/schemas.py

export type InvestigationStatus = "processing" | "completed" | "failed";
export type Verdict = "buy" | "buy_with_caution" | "avoid_purchase";
export type AgentStatus = "completed" | "failed" | "insufficient_data" | "timeout";

export interface InvestigationCreateResponse {
  investigation_id: string;
  status: InvestigationStatus;
  estimated_seconds: number;
}

export interface ProductSummary {
  id: string;
  title: string;
  current_price: number | null;
  currency: string;
  image_url: string | null;
}

export interface SellerSummary {
  id: string;
  display_name: string | null;
  marketplace_platform_type: string;
}

export interface RecommendationOut {
  verdict: Verdict;
  confidence: number;
  explanation: string;
  explanation_source: "template" | "llm";
  model_version: string;
}

export interface AgentSummary {
  agent: string;
  status: AgentStatus;
  verdict_signal: string | null;
  confidence: number;
}

export interface SellerIntelligenceData {
  seller_name: string | null;
  seller_type: string;
  is_official: boolean | null;
  seller_rating: number | null;
  seller_review_count: number | null;
  seller_profile_link: string | null;
  return_policy: string | null;
  warranty: string | null;
  business_verified: boolean | null;
  trust_score: number | null;
}

export interface PriceIntelligenceData {
  current_price: number | null;
  currency: string;
  list_price: number | null;
  official_brand_price: number | null;
  market_average: number | null;
  discount_percent: number | null;
  unrealistic_discount_detected: boolean;
  fairness_score: number | null;
}

export interface ReviewIntelligenceData {
  total_reviews: number;
  sentiment: string;
  sentiment_score: number | null;
  positive_keywords: string[];
  negative_keywords: string[];
  authenticity_score: number | null;
  authenticity_status: string;
}

export interface ScamIndicatorItem {
  name: string;
  severity: "low" | "medium" | "high" | "critical";
  description: string;
  detected: boolean;
}

export interface EvidenceSummaryItem {
  type: "supports" | "contradicts" | "neutral";
  icon: string;
  text: string;
}

export interface PurchaseIntelligence {
  overall_risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  recommendation: string;
  confidence_percent: number;
  seller_trust_score: number | null;
  price_fairness_score: number | null;
  review_authenticity_score: number | null;
  seller_intelligence: SellerIntelligenceData;
  price_intelligence: PriceIntelligenceData;
  review_intelligence: ReviewIntelligenceData;
  scam_indicators: ScamIndicatorItem[];
  evidence_summary: EvidenceSummaryItem[];
  why_recommendation: string;
}

export type InvestigationDataSource = "fetched" | "image_ocr" | "url_and_image";
export type InvestigationConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";

export interface ImageAnalysisData {
  product_name: string | "unavailable";
  product_name_confidence: "low" | "medium" | "unavailable";
  brand: string | "unavailable";
  price: number | "unavailable";
  currency: string | "unavailable";
  discount_percent: number | "unavailable";
  seller_name: string | "unavailable";
  platform_hint: string | "unavailable";
  model_sku: string | "unavailable";
  warranty_mentioned: boolean;
  contact_info_present: boolean;
  rating_text: string | "unavailable";
  promotional_claims: string[];
  ocr_text_excerpt: string;
  conflicts: string[];
}

export interface InvestigationConfidence {
  level: InvestigationConfidenceLevel;
  explanation: string;
}

export interface InvestigationDetail {
  investigation_id: string;
  status: InvestigationStatus;
  detected_platform: string | null;
  source_url: string;
  error_message: string | null;
  data_source: InvestigationDataSource;
  product: ProductSummary | null;
  seller: SellerSummary | null;
  recommendation: RecommendationOut | null;
  agent_summary: AgentSummary[];
  purchase_intelligence?: PurchaseIntelligence | null;
  seller_community_intelligence?: SellerCommunityIntelligence | null;
  review_intelligence_report?: ReviewIntelligenceReport | null;
  product_authenticity_report?: ProductAuthenticityReport | null;
  image_analysis?: ImageAnalysisData | null;
  investigation_confidence?: InvestigationConfidence | null;
}

export type AuthenticityLevel = "Strong" | "Moderate" | "Uncertain" | "Suspicious";
export type CounterfeitRisk = "Low" | "Medium" | "High";

export interface AuthenticityEvidenceSource {
  name: string;
  available: boolean;
  items_checked: number;
  note: string;
}

export interface ProductAuthenticityReport {
  authenticity_level: AuthenticityLevel;
  counterfeit_risk: CounterfeitRisk;
  authenticity_signals: string[];
  risk_signals: string[];
  evidence_sources: AuthenticityEvidenceSource[];
  ai_summary: string;
  platform_context: string;
}

export interface ReviewIntelligenceSource {
  name: string;
  available: boolean;
  items_collected: number;
  note: string;
}

export interface ReviewIntelligenceReport {
  overall_sentiment: string;
  sentiment_score: number | null;
  positive_pct: number | null;
  neutral_pct: number | null;
  negative_pct: number | null;
  total_items_analyzed: number;
  most_mentioned_positives: string[];
  most_mentioned_complaints: string[];
  product_quality_summary: string;
  delivery_experience_summary: string;
  refund_experience_summary: string;
  customer_support_experience: string;
  durability_feedback: string;
  size_fit_feedback: string;
  packaging_feedback: string;
  review_authenticity_score: number | null;
  review_authenticity_status: string;
  duplicate_review_count: number;
  spam_review_count: number;
  extremely_biased_detected: boolean;
  suspicious_behaviour: string[];
  ai_summary: string;
  ai_summary_source: "template" | "llm";
  sources_used: ReviewIntelligenceSource[];
  platform_context: string;
}

export interface SellerProfileData {
  seller_name: string;
  seller_type: string;
  seller_profile_link: string;
  is_official: boolean | null;
  seller_rating: number | null;
  seller_review_count: number | null;
  return_policy: string;
  refund_policy: string;
  warranty: string;
  contact_details: string;
  business_verified: boolean | null;
  business_registration_info: string;
  trust_score: number | null;
  transparency_score: number | null;
  complaint_count: number;
  prior_product_count: number;
  seller_summary: string;
  source_type: "official_brand" | "marketplace" | "independent_store" | "social_commerce" | "unknown_shopping";
  source_type_label: string;
  scoring_model: string;
  scoring_rationale: string;
  scoring_signals: string[];
  privacy_policy: string;
  terms_conditions: string;
  secure_payment: string;
  selection_reason: string;
  skip_reason: string;
  checks_performed: AdaptiveCheck[];
  checks_skipped: AdaptiveCheck[];
}

export interface AdaptiveCheck {
  id: string;
  label: string;
}

export interface CommunityIntelligenceData {
  overall_sentiment: string;
  sentiment_score: number | null;
  total_items_analyzed: number;
  positive_points: string[];
  complaints: string[];
  delivery_experience: string;
  refund_experience: string;
  product_quality_experience: string;
  community_summary: string;
}

export interface CommunitySourceInfo {
  name: string;
  available: boolean;
  items_analyzed: number;
  note: string;
}

export interface SellerCommunityIntelligence {
  seller_profile: SellerProfileData;
  community_intelligence: CommunityIntelligenceData;
  trust_signals: string[];
  risk_signals: string[];
  sources_used: CommunitySourceInfo[];
}

export interface EvidenceItemOut {
  id: string;
  source_type: string;
  polarity: "supports" | "contradicts" | "neutral";
  weight: number;
  summary: string;
  detail: Record<string, unknown>;
  occurred_at: string | null;
}

export interface AgentRunOut {
  agent: string;
  status: AgentStatus;
  verdict_signal: string | null;
  confidence: number;
  reasoning: string | null;
  duration_ms: number | null;
}

export interface InvestigationSummary {
  investigation_id: string;
  source_url: string;
  status: InvestigationStatus;
  created_at: string;
}

export interface PriceHistoryPoint {
  price: number;
  recorded_at: string;
}

export interface SampleInvestigation {
  investigation_id: string;
  verdict: Verdict;
  confidence: number;
  product_title: string;
  detected_platform: string | null;
}

export const ALL_AGENTS = [
  "platform_verification",
  "seller_intelligence",
  "review_intelligence",
  "historical_learning",
  "product_authenticity",
] as const;

export const AGENT_LABELS: Record<string, string> = {
  platform_verification: "Platform Verification",
  seller_intelligence: "Seller Intelligence",
  review_intelligence: "Review Intelligence",
  historical_learning: "Historical Learning",
  product_authenticity: "Product Authenticity",
};
