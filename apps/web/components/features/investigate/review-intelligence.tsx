"use client";

import { AlertTriangle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RadialScore } from "@/components/features/investigate/charts/radial-score";
import { SentimentDonut } from "@/components/features/investigate/charts/sentiment-donut";
import type { ReviewIntelligenceReport } from "@/types/investigation";

const NO_PUBLIC_DATA = "No public data available.";

export function ReviewIntelligenceSection({
  data,
  bare = false,
}: {
  data: ReviewIntelligenceReport | null | undefined;
  /** Renders just the content, no outer Card/title - for nesting inside
   * an already-titled container (e.g. the "Reviews" progressive-disclosure
   * tab). */
  bare?: boolean;
}) {
  if (!data) return null;

  const content = (
    <div className="flex flex-col gap-6">
        {/* Overall Customer Opinion */}
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold text-foreground">Overall Customer Opinion</h3>
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant={
                data.overall_sentiment === "Positive" ? "buy" : data.overall_sentiment === "Negative" ? "avoid" : "outline"
              }
            >
              {data.overall_sentiment}
            </Badge>
            {data.total_items_analyzed > 0 && (
              <span className="text-xs text-muted-foreground">
                based on {data.total_items_analyzed} publicly available item(s) - {data.platform_context}
              </span>
            )}
          </div>
          {data.total_items_analyzed > 0 &&
            data.positive_pct != null &&
            data.neutral_pct != null &&
            data.negative_pct != null && (
              <SentimentDonut positive={data.positive_pct} neutral={data.neutral_pct} negative={data.negative_pct} />
            )}
        </div>

        {/* Authenticity */}
        <div className="flex flex-wrap items-center gap-6">
          <RadialScore
            value={data.review_authenticity_score}
            label="Review Authenticity"
            sublabel={data.review_authenticity_status}
            size="md"
            unavailableText={NO_PUBLIC_DATA}
          />
          {(data.duplicate_review_count > 0 || data.spam_review_count > 0 || data.extremely_biased_detected) && (
            <div className="flex flex-col gap-1">
              {data.suspicious_behaviour.map((item) => (
                <span key={item} className="flex items-start gap-1.5 text-xs text-verdict-avoid">
                  <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" aria-hidden /> {item}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <PointList title="Most Mentioned Positives" items={data.most_mentioned_positives} />
          <PointList title="Most Mentioned Complaints" items={data.most_mentioned_complaints} />
        </div>

        <div className="h-px bg-border" />

        {/* Customer Experience Summary */}
        <div>
          <h3 className="text-sm font-semibold text-foreground">Customer Experience Summary</h3>
          <dl className="mt-2 grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
            <Field label="Product quality" value={data.product_quality_summary} />
            <Field label="Delivery experience" value={data.delivery_experience_summary} />
            <Field label="Refund experience" value={data.refund_experience_summary} />
            <Field label="Customer support" value={data.customer_support_experience} />
            <Field label="Durability feedback" value={data.durability_feedback} />
            <Field label="Size / fit feedback" value={data.size_fit_feedback} />
            <Field label="Packaging feedback" value={data.packaging_feedback} />
          </dl>
        </div>

        <div className="h-px bg-border" />

        {/* AI Review Summary */}
        <div>
          <h3 className="text-sm font-semibold text-foreground">AI Review Summary</h3>
          <p className="mt-1 text-sm text-muted-foreground">{data.ai_summary}</p>
          {data.ai_summary_source === "template" && data.ai_summary !== NO_PUBLIC_DATA && (
            <p className="mt-1 text-xs text-muted-foreground">
              Generated from TrustBuy&apos;s deterministic evidence template (no LLM API key configured for this
              deployment).
            </p>
          )}
        </div>

        {/* Sources Used */}
        <div>
          <h3 className="text-sm font-semibold text-foreground">Sources Used</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {data.sources_used.map((source) => (
              <Badge
                key={source.name}
                variant={source.available ? "outline" : "secondary"}
                title={source.available ? undefined : source.note || NO_PUBLIC_DATA}
              >
                {source.name}
                {source.available ? ` (${source.items_collected})` : ` - ${NO_PUBLIC_DATA}`}
              </Badge>
            ))}
          </div>
        </div>
    </div>
  );

  if (bare) return content;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Review Intelligence</CardTitle>
      </CardHeader>
      <CardContent>{content}</CardContent>
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3 sm:block">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-right text-foreground sm:text-left">{value}</dd>
    </div>
  );
}

function PointList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-foreground">{title}</h4>
      <ul className="mt-1 list-inside list-disc text-sm text-muted-foreground">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
