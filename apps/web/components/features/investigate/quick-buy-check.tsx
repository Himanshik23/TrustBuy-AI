"use client";

import { AlertTriangle, CheckCircle2, HelpCircle, ShoppingBag, XCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import type { InvestigationDetail } from "@/types/investigation";

type Status = "good" | "caution" | "bad" | "unknown";

const STATUS_META: Record<Status, { icon: typeof CheckCircle2; className: string }> = {
  good: { icon: CheckCircle2, className: "text-verdict-buy" },
  caution: { icon: AlertTriangle, className: "text-verdict-caution" },
  bad: { icon: XCircle, className: "text-verdict-avoid" },
  unknown: { icon: HelpCircle, className: "text-muted-foreground" },
};

interface Row {
  label: string;
  status: Status;
  note: string;
}

/** The "should I buy this?" answer in one glance - every value here is
 * read directly from scores/labels the investigation already computed
 * (seller trust, review sentiment, price fairness, product authenticity,
 * overall risk); nothing new is calculated. */
export function QuickBuyCheck({ investigation }: { investigation: InvestigationDetail }) {
  const rows = buildRows(investigation);
  if (rows.length === 0) return null;

  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="mb-3 flex items-center gap-2">
        <ShoppingBag className="h-4 w-4 text-primary" aria-hidden />
        <h3 className="text-sm font-semibold text-foreground">Quick Buy Check</h3>
      </div>
      <div className="grid grid-cols-1 gap-x-6 gap-y-2.5 sm:grid-cols-2">
        {rows.map((row) => {
          const meta = STATUS_META[row.status];
          const Icon = meta.icon;
          return (
            <div key={row.label} className="flex items-center justify-between gap-3 text-sm">
              <span className="text-muted-foreground">{row.label}</span>
              <span className={cn("flex items-center gap-1.5 font-medium", meta.className)}>
                <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />
                {row.note}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function buildRows(investigation: InvestigationDetail): Row[] {
  const rows: Row[] = [];

  const seller = investigation.seller_community_intelligence?.seller_profile;
  if (seller) {
    const trust = seller.trust_score;
    rows.push({
      label: "Seller",
      status: seller.is_official || (trust != null && trust >= 70) ? "good" : trust != null && trust >= 40 ? "caution" : trust != null ? "bad" : "unknown",
      note: seller.is_official ? "Official / verified" : trust != null ? (trust >= 70 ? "Trusted" : trust >= 40 ? "Limited history" : "Unverified") : "No data",
    });
  }

  const authenticity = investigation.product_authenticity_report;
  if (authenticity) {
    const level = authenticity.authenticity_level;
    rows.push({
      label: "Product",
      status: level === "Strong" || level === "Moderate" ? "good" : level === "Suspicious" ? "bad" : "unknown",
      note: level === "Strong" ? "Verified signals" : level === "Moderate" ? "Mostly consistent" : level === "Suspicious" ? "Authenticity concerns" : "Insufficient evidence",
    });
  }

  const review = investigation.review_intelligence_report;
  if (review && review.total_items_analyzed > 0) {
    rows.push({
      label: "Reviews",
      status: review.overall_sentiment === "Positive" ? "good" : review.overall_sentiment === "Negative" ? "bad" : "caution",
      note: review.overall_sentiment === "Positive" ? "Mostly positive" : review.overall_sentiment === "Negative" ? "Mostly negative" : "Mixed",
    });
  } else if (review) {
    rows.push({ label: "Reviews", status: "unknown", note: "No public data" });
  }

  const fairness = investigation.purchase_intelligence?.price_intelligence.fairness_score;
  if (fairness != null) {
    rows.push({
      label: "Price",
      status: fairness >= 70 ? "good" : fairness >= 40 ? "caution" : "bad",
      note: fairness >= 70 ? "Fair" : fairness >= 40 ? "Worth a look" : "Unusual",
    });
  }

  const riskLevel = investigation.purchase_intelligence?.overall_risk_level;
  if (riskLevel) {
    rows.push({
      label: "Risk",
      status: riskLevel === "LOW" ? "good" : riskLevel === "MEDIUM" ? "caution" : "bad",
      note: riskLevel.charAt(0) + riskLevel.slice(1).toLowerCase(),
    });
  }

  return rows;
}
