"use client";

import { Zap } from "lucide-react";

import type { InvestigationDetail } from "@/types/investigation";

/** Human, 2-3 sentence summary built entirely from fields the
 * investigation already computed - never a new analysis, never
 * fabricated. Degrades gracefully to neutral language wherever a signal
 * is missing instead of guessing. */
export function TldrSummary({ investigation }: { investigation: InvestigationDetail }) {
  const text = buildTldr(investigation);
  if (!text) return null;

  return (
    <div className="flex items-start gap-3 rounded-xl border border-primary/20 bg-primary/5 p-4">
      <Zap className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-primary">TL;DR</p>
        <p className="mt-1 text-sm text-foreground">{text}</p>
      </div>
    </div>
  );
}

function buildTldr(investigation: InvestigationDetail): string | null {
  const rec = investigation.recommendation;
  if (!rec) return null;

  const sellerTrust = investigation.seller_community_intelligence?.seller_profile.trust_score ?? null;
  const isOfficial = investigation.seller_community_intelligence?.seller_profile.is_official ?? null;
  const sentiment = investigation.review_intelligence_report?.overall_sentiment ?? null;
  const reviewsAnalyzed = investigation.review_intelligence_report?.total_items_analyzed ?? 0;
  const fairness = investigation.purchase_intelligence?.price_intelligence.fairness_score ?? null;
  const topConcern = investigation.purchase_intelligence?.evidence_summary.find((e) => e.type === "contradicts");

  const sellerPhrase = isOfficial
    ? "an official/verified seller"
    : sellerTrust != null
      ? sellerTrust >= 70
        ? "a credible seller"
        : sellerTrust >= 40
          ? "a seller with a limited track record"
          : "a seller TrustBuy couldn't fully verify"
      : "a seller TrustBuy has limited data on so far";

  const reviewPhrase =
    reviewsAnalyzed === 0
      ? "there isn't enough public review data yet to judge customer sentiment"
      : sentiment === "Positive"
        ? "customer feedback is mostly positive"
        : sentiment === "Negative"
          ? "customer feedback raises some concerns"
          : "customer feedback is mixed";

  const pricePhrase = fairness == null ? null : fairness >= 70 ? "the price looks fair" : fairness >= 40 ? "the price is worth a second look" : "the price looks unusual for this listing";

  let sentence1: string;
  if (rec.verdict === "buy") {
    sentence1 = `This listing from ${sellerPhrase} looks safe to buy.`;
  } else if (rec.verdict === "buy_with_caution") {
    sentence1 = `This listing from ${sellerPhrase} looks reasonable to buy, but a few things are worth checking first.`;
  } else {
    sentence1 = `TrustBuy found significant concerns with this listing and does not recommend buying it right now.`;
  }

  const parts = [sentence1, capitalize(reviewPhrase) + (pricePhrase ? `, and ${pricePhrase}.` : ".")];
  if (topConcern) {
    parts.push(`Biggest concern: ${topConcern.text}`);
  } else if (rec.verdict === "buy") {
    parts.push("No major red flags were found in this investigation.");
  }

  return parts.join(" ");
}

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
