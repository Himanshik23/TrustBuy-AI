"use client";

import { AlertTriangle, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AuthenticityLevel, CounterfeitRisk, ProductAuthenticityReport } from "@/types/investigation";

const LEVEL_VARIANT: Record<AuthenticityLevel, "buy" | "caution" | "secondary" | "avoid"> = {
  Strong: "buy",
  Moderate: "buy",
  Uncertain: "secondary",
  Suspicious: "avoid",
};

const RISK_VARIANT: Record<CounterfeitRisk, "buy" | "caution" | "avoid"> = {
  Low: "buy",
  Medium: "caution",
  High: "avoid",
};

export function ProductAuthenticitySection({
  data,
  bare = false,
}: {
  data: ProductAuthenticityReport | null | undefined;
  /** Renders just the content, no outer Card/title - for nesting inside
   * an already-titled container (e.g. the "Product" progressive-disclosure
   * tab). */
  bare?: boolean;
}) {
  if (!data) return null;

  const content = (
    <div className="flex flex-col gap-6">
        <div className="flex flex-wrap items-center gap-6">
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">Authenticity Level</span>
            <Badge variant={LEVEL_VARIANT[data.authenticity_level]} className="w-fit text-sm">
              {data.authenticity_level}
            </Badge>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">Counterfeit Risk</span>
            <Badge variant={RISK_VARIANT[data.counterfeit_risk]} className="w-fit text-sm">
              {data.counterfeit_risk}
            </Badge>
          </div>
          <span className="text-xs text-muted-foreground">based on {data.platform_context.toLowerCase()} evidence</span>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <SignalList title="Authenticity Signals" icon={ShieldCheck} items={data.authenticity_signals} tone="buy" />
          <SignalList title="Risk Signals" icon={AlertTriangle} items={data.risk_signals} tone="avoid" />
        </div>

        <div className="h-px bg-border" />

        <div>
          <h3 className="text-sm font-semibold text-foreground">AI Summary</h3>
          <p className="mt-1 text-sm text-muted-foreground">{data.ai_summary}</p>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-foreground">Evidence / Sources</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {data.evidence_sources.map((source) => (
              <Badge key={source.name} variant={source.available ? "outline" : "secondary"} title={source.note || undefined}>
                {source.name}
                {source.available ? ` (${source.items_checked})` : " - unavailable"}
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
        <CardTitle className="text-base">Product Authenticity</CardTitle>
      </CardHeader>
      <CardContent>{content}</CardContent>
    </Card>
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
      {items.length === 0 ? (
        <p className="mt-1 text-sm text-muted-foreground">None identified.</p>
      ) : (
        <ul className="mt-1 flex flex-col gap-1.5">
          {items.map((item) => (
            <li key={item} className="flex items-start gap-2 text-sm text-muted-foreground">
              <Icon className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${colorClass}`} aria-hidden />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
