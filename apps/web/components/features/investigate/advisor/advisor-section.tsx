"use client";

import * as React from "react";
import { motion, useReducedMotion } from "framer-motion";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronDown,
  Lightbulb,
  Loader2,
  MinusCircle,
  ShoppingBag,
  Sparkles,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useAdvisorReport } from "@/hooks/use-advisor";
import { TypingReveal } from "@/components/features/investigate/advisor/typing-reveal";
import { RadialScore } from "@/components/features/investigate/charts/radial-score";
import type { BuyDecisionType, RegretProbability } from "@/types/advisor";

const DECISION_STYLES: Record<BuyDecisionType, { className: string; icon: typeof CheckCircle2 }> = {
  buy_now: { className: "bg-verdict-buy/15 text-verdict-buy border-verdict-buy/30", icon: CheckCircle2 },
  wait_for_better_price: { className: "bg-verdict-caution/15 text-verdict-caution border-verdict-caution/30", icon: MinusCircle },
  buy_from_different_seller: { className: "bg-verdict-caution/15 text-verdict-caution border-verdict-caution/30", icon: AlertTriangle },
  buy_with_caution: { className: "bg-verdict-caution/15 text-verdict-caution border-verdict-caution/30", icon: AlertTriangle },
  avoid_purchase: { className: "bg-verdict-avoid/15 text-verdict-avoid border-verdict-avoid/30", icon: AlertTriangle },
  pending: { className: "bg-secondary text-muted-foreground border-border", icon: Loader2 },
};

const REGRET_STYLES: Record<RegretProbability, string> = {
  "Very Low": "bg-verdict-buy/15 text-verdict-buy border-verdict-buy/30",
  Low: "bg-verdict-buy/15 text-verdict-buy border-verdict-buy/30",
  Medium: "bg-verdict-caution/15 text-verdict-caution border-verdict-caution/30",
  High: "bg-verdict-avoid/15 text-verdict-avoid border-verdict-avoid/30",
  Unknown: "bg-secondary text-muted-foreground border-border",
};

/** AI Shopping Advisor & Buyer Regret Prediction - purely additive,
 * rendered below the existing recommendation card. Consumes the
 * already-completed investigation only (GET .../advisor); never triggers
 * a new investigation. */
export function AdvisorSection({ investigationId }: { investigationId: string }) {
  const { data, isLoading, isError } = useAdvisorReport(investigationId, true);
  const reduce = useReducedMotion();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShoppingBag className="h-4 w-4 text-primary" aria-hidden /> AI Shopping Advisor
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Generating shopping advice...
        </CardContent>
      </Card>
    );
  }

  if (isError || !data) return null;

  const decisionStyle = DECISION_STYLES[data.buy_decision.decision] ?? DECISION_STYLES.pending;
  const DecisionIcon = decisionStyle.icon;

  return (
    <motion.div
      initial={reduce ? undefined : { opacity: 0, y: 16 }}
      animate={reduce ? undefined : { opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShoppingBag className="h-4 w-4 text-primary" aria-hidden /> AI Shopping Advisor
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Personalized advice generated from this investigation&apos;s own evidence - never a new analysis.
          </p>
        </CardHeader>
        <CardContent className="flex flex-col gap-8">
          {/* Feature 3: Should You Buy Now? decision card */}
          <div
            className={cn(
              "flex flex-col gap-2 rounded-2xl border p-5 shadow-sm backdrop-blur-xl sm:flex-row sm:items-center sm:justify-between",
              decisionStyle.className
            )}
          >
            <div className="flex items-center gap-3">
              <DecisionIcon className="h-6 w-6 shrink-0" aria-hidden />
              <div>
                <p className="text-lg font-bold tracking-tight">{data.buy_decision.label}</p>
                <p className="text-sm opacity-90">{data.buy_decision.explanation}</p>
              </div>
            </div>
          </div>

          {/* Feature 2: Buyer Regret Prediction */}
          <div className="flex flex-col gap-3">
            <h3 className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
              <Sparkles className="h-4 w-4 text-primary" aria-hidden /> Buyer Regret Prediction
            </h3>
            <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
              <RadialScore
                value={data.regret_prediction.score}
                label="Regret Likelihood"
                sublabel={data.regret_prediction.probability}
                invert
                size="sm"
                suffix="%"
                unavailableText={data.regret_prediction.probability}
              />
              <div className="flex flex-1 flex-col gap-2">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-xs text-muted-foreground">Likelihood of Buyer Regret</span>
                  <Badge className={cn("border px-3 py-1 text-sm font-semibold", REGRET_STYLES[data.regret_prediction.probability])}>
                    {data.regret_prediction.probability}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">{data.regret_prediction.ai_summary}</p>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wide text-verdict-avoid">
                  Reasons that may cause regret
                </h4>
                <ul className="mt-1.5 flex flex-col gap-1 text-sm text-muted-foreground">
                  {data.regret_prediction.reasons_increasing.map((reason) => (
                    <li key={reason} className="flex items-start gap-1.5">
                      <span className="mt-0.5 text-verdict-avoid">•</span> {reason}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wide text-verdict-buy">Reasons reducing regret</h4>
                <ul className="mt-1.5 flex flex-col gap-1 text-sm text-muted-foreground">
                  {data.regret_prediction.reasons_reducing.map((reason) => (
                    <li key={reason} className="flex items-start gap-1.5">
                      <span className="mt-0.5 text-verdict-buy">•</span> {reason}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          <div className="h-px bg-border" />

          {/* Feature 4: Best Buying Tips */}
          <div className="flex flex-col gap-2">
            <h3 className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
              <Lightbulb className="h-4 w-4 text-primary" aria-hidden /> Best Buying Tips
            </h3>
            <ul className="flex flex-col gap-1.5 text-sm text-muted-foreground">
              {data.tips.map((tip) => (
                <li key={tip} className="flex items-start gap-1.5">
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-verdict-buy" aria-hidden /> {tip}
                </li>
              ))}
            </ul>
          </div>

          <div className="h-px bg-border" />

          {/* Feature 1: AI Shopping Advisor briefing (auto Q&A) */}
          <BriefingList items={data.briefing} />
        </CardContent>
      </Card>
    </motion.div>
  );
}

function BriefingList({ items }: { items: { question: string; answer: string }[] }) {
  const [openIndex, setOpenIndex] = React.useState<number | null>(0);
  return (
    <div className="flex flex-col gap-2">
      <h3 className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
        <Bot className="h-4 w-4 text-primary" aria-hidden /> Ask TrustBuy AI
      </h3>
      <div className="flex flex-col divide-y divide-border rounded-lg border border-border">
        {items.map((item, i) => {
          const open = openIndex === i;
          return (
            <div key={item.question}>
              <button
                type="button"
                onClick={() => setOpenIndex(open ? null : i)}
                aria-expanded={open}
                className="flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left text-sm font-medium hover:bg-secondary"
              >
                {item.question}
                <ChevronDown className={cn("h-4 w-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} aria-hidden />
              </button>
              {open && (
                <div className="px-4 pb-3 text-sm text-muted-foreground">
                  <TypingReveal text={item.answer} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
