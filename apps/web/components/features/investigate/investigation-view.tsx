"use client";

import * as React from "react";
import axios from "axios";
import {
  AlertTriangle,
  Building2,
  ExternalLink,
  Loader2,
  Package,
  Star,
  Tag,
  UserCheck,
  Users,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CollapsibleSection } from "@/components/ui/collapsible-section";
import { useEvidence, useInvestigation } from "@/hooks/use-investigation";
import { AgentProgressList } from "@/components/features/investigate/agent-progress-list";
import { EvidenceTimeline } from "@/components/features/investigate/evidence-timeline";
import { VerdictBadge } from "@/components/features/investigate/verdict-badge";
import { ReportForm } from "@/components/features/community/report-form";
import { ReportsList } from "@/components/features/community/reports-list";
import { CopilotPanel } from "@/components/features/copilot/copilot-panel";
import { ExportReportButton } from "@/components/features/investigate/export-report-button";
import { IntakeChecklist } from "@/components/features/investigate/intake-checklist";
import { ConfidenceBasisNote } from "@/components/features/investigate/confidence-basis-note";
import { SellerCommunityIntelligenceSection } from "@/components/features/investigate/seller-community-intelligence";
import { ProductAuthenticitySection } from "@/components/features/investigate/product-authenticity";
import { ReviewIntelligenceSection } from "@/components/features/investigate/review-intelligence";
import { PriceSummary } from "@/components/features/investigate/price-summary";
import { BusinessSummary } from "@/components/features/investigate/business-summary";
import { TldrSummary } from "@/components/features/investigate/tldr-summary";
import { QuickBuyCheck } from "@/components/features/investigate/quick-buy-check";
import { WhySummary } from "@/components/features/investigate/why-summary";
import { AdvisorSection } from "@/components/features/investigate/advisor/advisor-section";
import { RadialScore, type ScoreTone } from "@/components/features/investigate/charts/radial-score";
import { AgentConfidenceChart } from "@/components/features/investigate/charts/agent-confidence-chart";
import { EvidenceContributionChart } from "@/components/features/investigate/charts/evidence-contribution-chart";
import { ReportSkeleton } from "@/components/features/investigate/report-skeleton";
import { StickyVerdictBar } from "@/components/features/investigate/sticky-verdict-bar";
import { AgentActivity } from "@/components/features/investigate/agent-activity";
import { ImageAnalysisSection, InvestigationConfidenceBadge } from "@/components/features/investigate/image-analysis-section";
import type { InvestigationDetail, Verdict } from "@/types/investigation";

const VERDICT_TONE: Record<string, ScoreTone> = {
  buy: "buy",
  buy_with_caution: "caution",
  avoid_purchase: "avoid",
};

const RISK_VARIANT: Record<string, "buy" | "caution" | "avoid"> = {
  LOW: "buy",
  MEDIUM: "caution",
  HIGH: "avoid",
  CRITICAL: "avoid",
};

const HEADLINE: Record<Verdict, string> = {
  buy: "This looks like a safe purchase based on TrustBuy's analysis.",
  buy_with_caution: "This purchase looks reasonable, but a few things are worth checking first.",
  avoid_purchase: "TrustBuy found significant concerns with this listing.",
};

export function InvestigationView({ id }: { id: string }) {
  const { data: investigation, isLoading, isError, error, refetch, isRefetching } = useInvestigation(id);
  const isDone = investigation?.status === "completed";
  const { data: evidence } = useEvidence(id, isDone);
  const verdictAnchorRef = React.useRef<HTMLDivElement>(null);
  const [showFullExplanation, setShowFullExplanation] = React.useState(false);

  if (isLoading) {
    return <ReportSkeleton />;
  }

  if (isError || !investigation) {
    // A 404 really does mean "this investigation doesn't exist" - anything
    // else (a dropped connection, a transient server error) is a different
    // problem and shouldn't be described that way or leave the user stuck.
    const status = axios.isAxiosError(error) ? error.response?.status : undefined;
    const message =
      status === 404
        ? "We couldn't find this investigation. The link may be incorrect, or it may have been removed."
        : "Something went wrong loading this investigation. This is usually temporary.";
    return (
      <div className="flex flex-col items-start gap-3">
        <p className="text-sm text-destructive">{message}</p>
        {status !== 404 && (
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isRefetching}>
            {isRefetching ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Retrying...
              </>
            ) : (
              "Try again"
            )}
          </Button>
        )}
      </div>
    );
  }

  if (investigation.status === "failed") {
    return (
      <Card className="border-destructive/30">
        <CardContent className="flex items-start gap-3 py-6">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" aria-hidden />
          <div>
            <p className="font-medium text-foreground">This investigation could not be completed.</p>
            <p className="mt-1 text-sm text-muted-foreground">{investigation.error_message ?? "Unknown error."}</p>
            <a
              href={investigation.source_url}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-flex items-center gap-1 text-sm text-primary hover:underline"
            >
              View source URL <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </CardContent>
      </Card>
    );
  }

  const riskLevel = investigation.purchase_intelligence?.overall_risk_level;

  return (
    <div className="flex flex-col gap-6">
      {investigation.recommendation && (
        <StickyVerdictBar
          anchorRef={verdictAnchorRef}
          verdict={investigation.recommendation.verdict}
          confidence={investigation.recommendation.confidence}
          title={investigation.product?.title ?? "Investigation"}
        />
      )}

      {/* PRODUCT + SELLER */}
      <Card>
        <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
          <div className="flex items-start gap-4">
            {investigation.product?.image_url && (
              <img
                src={investigation.product.image_url}
                alt={investigation.product.title}
                className="h-20 w-20 shrink-0 rounded-lg border border-border bg-surface-elevated object-cover"
                loading="lazy"
                // The source's own hotlinked image can 404/expire independently
                // of the investigation itself - hide the broken-image icon
                // rather than show a visibly broken box; every other field
                // still renders normally either way.
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                }}
              />
            )}
            <div>
              <CardTitle className="text-xl">{investigation.product?.title ?? "Investigating listing..."}</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                {investigation.seller?.display_name ?? "Unknown seller"}
                {investigation.detected_platform && (
                  <Badge variant="outline" className="ml-2 align-middle">
                    {investigation.detected_platform}
                  </Badge>
                )}
              </p>
              <div className="mt-3">
                <IntakeChecklist detectedPlatform={investigation.detected_platform} status={investigation.status} />
              </div>
            </div>
          </div>
          {investigation.product?.current_price != null && (
            <p className="text-lg font-semibold">
              {investigation.product.currency} {investigation.product.current_price.toFixed(2)}
            </p>
          )}
        </CardHeader>
      </Card>

      {/* LEVEL 1: QUICK DECISION + LEVEL 2: TL;DR / QUICK BUY CHECK / WHY? */}
      {investigation.recommendation ? (
        <Card ref={verdictAnchorRef}>
          <CardContent className="flex flex-col gap-5 py-6">
            <div className="flex items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-2">
                <VerdictBadge verdict={investigation.recommendation.verdict} confidence={investigation.recommendation.confidence} />
                <InvestigationConfidenceBadge confidence={investigation.investigation_confidence} />
                {riskLevel && (
                  <Badge variant={RISK_VARIANT[riskLevel] ?? "secondary"} className="text-xs">
                    {riskLevel.charAt(0) + riskLevel.slice(1).toLowerCase()} risk
                  </Badge>
                )}
              </div>
              <ExportReportButton investigationId={investigation.investigation_id} />
            </div>

            <div className="flex flex-col items-start gap-5 sm:flex-row sm:items-center">
              <RadialScore
                value={Math.round(investigation.recommendation.confidence * 100)}
                label="Confidence"
                tone={VERDICT_TONE[investigation.recommendation.verdict]}
                size="lg"
                suffix="%"
              />
              <div className="flex flex-1 flex-col gap-2">
                <p className="text-base font-medium text-foreground">{HEADLINE[investigation.recommendation.verdict]}</p>
                <button
                  type="button"
                  onClick={() => setShowFullExplanation((v) => !v)}
                  className="self-start text-xs font-medium text-primary hover:underline"
                >
                  {showFullExplanation ? "Hide full explanation" : "Read full explanation"}
                </button>
                {showFullExplanation && (
                  <div className="flex flex-col gap-2 rounded-lg bg-secondary/40 p-3">
                    <p className="text-sm text-foreground">{investigation.recommendation.explanation}</p>
                    <ConfidenceBasisNote agentSummary={investigation.agent_summary} />
                    {investigation.recommendation.explanation_source === "template" && (
                      <p className="text-xs text-muted-foreground">
                        Generated from TrustBuy&apos;s deterministic evidence template (no LLM API key configured for
                        this deployment - see DECISIONS.md ADR-010).
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>

            <TldrSummary investigation={investigation} />
            <QuickBuyCheck investigation={investigation} />
            <WhySummary investigation={investigation} />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Investigating...</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <AgentActivity agentSummary={investigation.agent_summary} investigationStatus={investigation.status} />
            <AgentProgressList agentSummary={investigation.agent_summary} investigationStatus={investigation.status} />
          </CardContent>
        </Card>
      )}

      {isDone && <AdvisorSection investigationId={investigation.investigation_id} />}

      {isDone && <ImageAnalysisSection analysis={investigation.image_analysis} />}

      {/* LEVEL 3: DEEP DIVE */}
      {isDone && (
        <div className="flex flex-col gap-3">
          <h2 className="px-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Detailed Investigation
          </h2>

          <CollapsibleSection title="Seller" icon={UserCheck} summary={sellerSummary(investigation)}>
            <SellerCommunityIntelligenceSection data={investigation.seller_community_intelligence} bare />
          </CollapsibleSection>

          <CollapsibleSection title="Reviews" icon={Star} summary={reviewsSummary(investigation)}>
            <ReviewIntelligenceSection data={investigation.review_intelligence_report} bare />
          </CollapsibleSection>

          <CollapsibleSection title="Price" icon={Tag} summary={priceSummary(investigation)}>
            <PriceSummary
              data={investigation.purchase_intelligence?.price_intelligence}
              currency={investigation.product?.currency}
            />
          </CollapsibleSection>

          <CollapsibleSection title="Product" icon={Package} summary={productSummary(investigation)}>
            <ProductAuthenticitySection data={investigation.product_authenticity_report} bare />
          </CollapsibleSection>

          {investigation.product && (
            <CollapsibleSection title="Community" icon={Users} summary={communitySummary(investigation)}>
              <div className="flex flex-col gap-4">
                <ReportForm productId={investigation.product.id} />
                <ReportsList productId={investigation.product.id} />
              </div>
            </CollapsibleSection>
          )}

          <CollapsibleSection title="Business" icon={Building2} summary={businessSummary(investigation)}>
            <BusinessSummary seller={investigation.seller_community_intelligence?.seller_profile} />
          </CollapsibleSection>
        </div>
      )}

      {/* Evidence & Sources */}
      {isDone && (
        <CollapsibleSection title="Evidence & Sources" summary={`${evidence?.length ?? 0} evidence item(s) collected`}>
          <div className="flex flex-col gap-5">
            <p className="text-xs text-muted-foreground">
              What actually moved the verdict - each bar is a real evidence item, sized by how much weight it carried.
            </p>
            <EvidenceContributionChart items={evidence ?? []} />
            <EvidenceTimeline items={evidence ?? []} />
          </div>
        </CollapsibleSection>
      )}

      {/* Technical Details */}
      {isDone && (
        <CollapsibleSection title="Technical Details" summary="Agent-by-agent confidence breakdown">
          <div className="flex flex-col gap-5">
            <AgentConfidenceChart agentSummary={investigation.agent_summary} />
            <AgentProgressList agentSummary={investigation.agent_summary} investigationStatus={investigation.status} />
          </div>
        </CollapsibleSection>
      )}

      {isDone && <CopilotPanel investigationId={investigation.investigation_id} />}
    </div>
  );
}

function sellerSummary(investigation: InvestigationDetail): string {
  const seller = investigation.seller_community_intelligence?.seller_profile;
  if (!seller) return "Data unavailable";
  const trust = seller.trust_score;
  const label = seller.is_official ? "Official / verified" : trust != null ? (trust >= 70 ? "Trusted" : trust >= 40 ? "Limited history" : "Unverified") : "No data";
  const rating = seller.seller_rating != null ? ` · ${seller.seller_rating}/5.0` : "";
  return `${label}${rating}`;
}

function reviewsSummary(investigation: InvestigationDetail): string {
  const review = investigation.review_intelligence_report;
  if (!review || review.total_items_analyzed === 0) return "No public data";
  const pct = review.positive_pct != null ? ` · ${review.positive_pct}% positive` : "";
  return `${review.overall_sentiment}${pct}`;
}

function priceSummary(investigation: InvestigationDetail): string {
  const pi = investigation.purchase_intelligence?.price_intelligence;
  if (!pi || pi.current_price == null) return "Insufficient evidence";
  const fairness = pi.fairness_score;
  const label = fairness == null ? "" : fairness >= 70 ? "Fair · " : fairness >= 40 ? "Worth a look · " : "Unusual · ";
  const currency = investigation.product?.currency || pi.currency;
  return `${label}${currency} ${pi.current_price.toFixed(2)}`;
}

function productSummary(investigation: InvestigationDetail): string {
  const report = investigation.product_authenticity_report;
  if (!report) return "Insufficient evidence to determine authenticity.";
  return `${report.authenticity_level} · ${report.counterfeit_risk} counterfeit risk`;
}

function communitySummary(investigation: InvestigationDetail): string {
  const community = investigation.seller_community_intelligence?.community_intelligence;
  if (!community || community.total_items_analyzed === 0) return "No community reports yet";
  return `${community.total_items_analyzed} item(s) analyzed`;
}

function businessSummary(investigation: InvestigationDetail): string {
  const seller = investigation.seller_community_intelligence?.seller_profile;
  if (!seller) return "Data unavailable";
  if (seller.business_verified == null) return "Data unavailable";
  return seller.business_verified ? "Verified" : "Not verified";
}
