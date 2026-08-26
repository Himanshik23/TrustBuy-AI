"use client";

import { AlertTriangle, Image as ImageIcon, ShieldQuestion } from "lucide-react";

import { CollapsibleSection } from "@/components/ui/collapsible-section";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ImageAnalysisData, InvestigationConfidence } from "@/types/investigation";

const CONFIDENCE_STYLES: Record<string, string> = {
  HIGH: "bg-verdict-buy/15 text-verdict-buy border-verdict-buy/30",
  MEDIUM: "bg-verdict-caution/15 text-verdict-caution border-verdict-caution/30",
  LOW: "bg-verdict-avoid/15 text-verdict-avoid border-verdict-avoid/30",
};

/** Overall Investigation Confidence (Feature: "Image-Based Product
 * Analysis + Accuracy Improvement") - a holistic, rule-based read on how
 * much reliable evidence this investigation actually had, deliberately
 * separate from the per-verdict confidence percentage next to the badge. */
export function InvestigationConfidenceBadge({ confidence }: { confidence: InvestigationConfidence | null | undefined }) {
  if (!confidence) return null;
  return (
    <Badge
      className={cn("border px-2.5 py-1 text-xs font-semibold", CONFIDENCE_STYLES[confidence.level] ?? "")}
      title={confidence.explanation}
    >
      <ShieldQuestion className="mr-1 h-3 w-3" aria-hidden />
      {confidence.level} CONFIDENCE
    </Badge>
  );
}

function field(label: string, value: string | number | boolean | null | undefined) {
  const display =
    value === "unavailable" || value === null || value === undefined || value === ""
      ? "Not found in the image"
      : typeof value === "boolean"
        ? value
          ? "Yes"
          : "No"
        : String(value);
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("font-medium", display === "Not found in the image" && "text-muted-foreground italic")}>
        {display}
      </span>
    </div>
  );
}

/** Everything genuinely extracted from a user-uploaded image via OCR
 * (app/image_analysis.py) - never fabricated: a field the OCR/regex pass
 * could not find is shown as "Not found in the image", not guessed. */
export function ImageAnalysisSection({ analysis }: { analysis: ImageAnalysisData | null | undefined }) {
  if (!analysis) return null;

  const hasConflicts = analysis.conflicts && analysis.conflicts.length > 0;

  return (
    <div className="flex flex-col gap-3">
      {hasConflicts && (
        <div className="flex items-start gap-3 rounded-xl border border-verdict-avoid/40 bg-verdict-avoid/10 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-verdict-avoid" aria-hidden />
          <div>
            <p className="text-sm font-semibold text-verdict-avoid">Information conflict detected</p>
            <ul className="mt-1 flex flex-col gap-1 text-sm text-foreground">
              {analysis.conflicts.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
            <p className="mt-1 text-xs text-muted-foreground">
              The uploaded image and the fetched listing page do not fully agree - TrustBuy has not silently chosen
              one over the other.
            </p>
          </div>
        </div>
      )}

      <CollapsibleSection
        title="Information Extracted from Your Image"
        icon={ImageIcon}
        summary={
          analysis.product_name !== "unavailable" ? analysis.product_name : "Limited information could be read from the image"
        }
      >
        <div className="flex flex-col gap-2">
          {field("Product name", analysis.product_name)}
          {analysis.product_name !== "unavailable" && analysis.product_name_confidence !== "unavailable" && (
            <p className="text-xs text-muted-foreground">
              (Best-effort read from the image text - {analysis.product_name_confidence} confidence, not independently verified.)
            </p>
          )}
          {field("Brand", analysis.brand)}
          {field("Price", analysis.price === "unavailable" ? "unavailable" : `${analysis.price} ${analysis.currency !== "unavailable" ? analysis.currency : ""}`)}
          {field("Discount", analysis.discount_percent === "unavailable" ? "unavailable" : `${analysis.discount_percent}%`)}
          {field("Seller", analysis.seller_name)}
          {field("Model / SKU", analysis.model_sku)}
          {field("Warranty mentioned", analysis.warranty_mentioned)}
          {field("Contact info present", analysis.contact_info_present)}
          {field("Rating shown", analysis.rating_text)}
          {analysis.promotional_claims.length > 0 && (
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="text-muted-foreground">Promotional claims detected</span>
              <span className="font-medium">{analysis.promotional_claims.join(", ")}</span>
            </div>
          )}
          <p className="mt-2 text-xs text-muted-foreground">
            Extracted directly from the image you uploaded via OCR - self-supplied, not independently verified by
            TrustBuy the way a fetched listing page is.
          </p>
        </div>
      </CollapsibleSection>
    </div>
  );
}
