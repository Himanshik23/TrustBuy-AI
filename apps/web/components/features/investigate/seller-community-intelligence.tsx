"use client";

import { Check, ExternalLink, Minus, ShieldCheck, ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RadialScore } from "@/components/features/investigate/charts/radial-score";
import type { SellerCommunityIntelligence } from "@/types/investigation";

const UNAVAILABLE = "Data unavailable";

export function SellerCommunityIntelligenceSection({
  data,
  bare = false,
}: {
  data: SellerCommunityIntelligence | null | undefined;
  /** Renders just the content, no outer Card/title - for nesting inside
   * an already-titled container (e.g. the "Sellers" progressive-disclosure
   * tab), so the report never shows the same heading twice. */
  bare?: boolean;
}) {
  if (!data) return null;
  const { seller_profile: seller, community_intelligence: community, trust_signals, risk_signals, sources_used } = data;

  const content = (
    <div className="flex flex-col gap-6">
      {/* Adaptive Investigation Engine: which checklist was loaded for
            this platform, and which checks were intentionally skipped. */}
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-foreground">Investigation Checklist</h3>
            <Badge variant="outline">{seller.source_type_label}</Badge>
          </div>
          <div className="flex flex-wrap gap-2">
            {seller.checks_performed.map((c) => (
              <Badge key={c.id} variant="buy" className="gap-1">
                <Check className="h-3 w-3" aria-hidden /> {c.label}
              </Badge>
            ))}
            {seller.checks_skipped.map((c) => (
              <Badge key={c.id} variant="secondary" className="gap-1" title={`Skipped: ${seller.skip_reason}`}>
                <Minus className="h-3 w-3" aria-hidden /> {c.label} (N/A)
              </Badge>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            This model was selected because {seller.selection_reason}. Checks marked N/A are intentionally skipped -
            not relevant for this platform type - and never count against the trust score.
          </p>
        </div>

        <div className="h-px bg-border" />

        {/* Seller Profile */}
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold text-foreground">Seller Profile</h3>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-foreground">{seller.seller_name}</span>
            <Badge variant="outline">{seller.seller_type}</Badge>
            {seller.is_official && <Badge variant="buy">Official Seller</Badge>}
            {seller.seller_profile_link !== UNAVAILABLE && (
              <a
                href={seller.seller_profile_link}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
              >
                Seller profile <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
          <dl className="grid grid-cols-1 gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
            <Field label="Seller rating" value={seller.seller_rating != null ? `${seller.seller_rating}/5.0` : UNAVAILABLE} />
            <Field
              label="Total seller ratings"
              value={seller.seller_review_count != null ? String(seller.seller_review_count) : UNAVAILABLE}
            />
            <Field label="Return policy" value={seller.return_policy} />
            <Field label="Refund policy" value={seller.refund_policy} />
            <Field label="Warranty" value={seller.warranty} />
            <Field label="Contact details" value={seller.contact_details} />
            <Field
              label="Business verification"
              value={seller.business_verified == null ? UNAVAILABLE : seller.business_verified ? "Verified" : "Not verified"}
            />
            <Field label="GST / company information" value={seller.business_registration_info} />
            <Field label="Privacy Policy" value={seller.privacy_policy} />
            <Field label="Terms & Conditions" value={seller.terms_conditions} />
            <Field label="Secure payment methods" value={seller.secure_payment} />
          </dl>
        </div>

        {/* Trust + Transparency scores */}
        <div className="flex flex-wrap gap-6">
          <RadialScore value={seller.trust_score} label="Seller Trust Score" size="md" />
          <RadialScore value={seller.transparency_score} label="Seller Transparency Score" size="md" />
        </div>

        {/* Seller Summary */}
        <div>
          <h3 className="text-sm font-semibold text-foreground">Seller Summary</h3>
          <p className="mt-1 text-sm text-muted-foreground">{seller.seller_summary}</p>
          <p className="mt-2 text-xs text-muted-foreground">
            <span className="font-medium text-foreground">Scoring model: {seller.scoring_model}.</span>{" "}
            {seller.scoring_rationale}
          </p>
        </div>

        <div className="h-px bg-border" />

        {/* Community sentiment */}
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold text-foreground">Overall Community Sentiment</h3>
          <div className="flex items-center gap-2">
            <Badge
              variant={
                community.overall_sentiment === "Positive"
                  ? "buy"
                  : community.overall_sentiment === "Negative"
                    ? "avoid"
                    : "outline"
              }
            >
              {community.overall_sentiment}
            </Badge>
            {community.sentiment_score != null && (
              <span className="text-xs text-muted-foreground">score {community.sentiment_score.toFixed(2)}</span>
            )}
            <span className="text-xs text-muted-foreground">
              based on {community.total_items_analyzed} publicly available item(s)
            </span>
          </div>
          <p className="text-sm text-muted-foreground">{community.community_summary}</p>
          <dl className="mt-1 grid grid-cols-1 gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
            <Field label="Delivery experience" value={community.delivery_experience} />
            <Field label="Refund experience" value={community.refund_experience} />
            <Field label="Product quality experience" value={community.product_quality_experience} />
          </dl>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <PointList title="Top Positive Points" items={community.positive_points} />
          <PointList title="Top Complaints" items={community.complaints} />
        </div>

        <div className="h-px bg-border" />

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <SignalList title="Trust Signals" icon={ShieldCheck} items={trust_signals} tone="buy" />
          <SignalList title="Risk Signals" icon={ShieldAlert} items={risk_signals} tone="avoid" />
        </div>

        {/* Sources used */}
        <div>
          <h3 className="text-sm font-semibold text-foreground">Sources Used</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {sources_used.map((source) => (
              <Badge key={source.name} variant={source.available ? "outline" : "secondary"} title={source.note || undefined}>
                {source.name}
                {source.available ? ` (${source.items_analyzed})` : " - unavailable"}
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
        <CardTitle className="text-base">Seller &amp; Community Intelligence</CardTitle>
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

function SignalList({
  title,
  icon: Icon,
  items,
  tone,
}: {
  title: string;
  icon: typeof ShieldCheck;
  items: string[];
  tone: "buy" | "avoid";
}) {
  const colorClass = tone === "buy" ? "text-verdict-buy" : "text-verdict-avoid";
  return (
    <div>
      <h4 className="text-sm font-semibold text-foreground">{title}</h4>
      <ul className="mt-1 flex flex-col gap-1.5">
        {items.map((item) => (
          <li key={item} className="flex items-start gap-2 text-sm text-muted-foreground">
            <Icon className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${colorClass}`} aria-hidden />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
