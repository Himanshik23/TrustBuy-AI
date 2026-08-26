import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import type { Verdict } from "@/types/investigation";

const VERDICT_META: Record<Verdict, { label: string; icon: typeof CheckCircle2; className: string }> = {
  buy: { label: "BUY", icon: CheckCircle2, className: "bg-verdict-buy/15 text-verdict-buy border-verdict-buy/30" },
  buy_with_caution: {
    label: "BUY WITH CAUTION",
    icon: AlertTriangle,
    className: "bg-verdict-caution/15 text-verdict-caution border-verdict-caution/30",
  },
  avoid_purchase: {
    label: "AVOID PURCHASE",
    icon: XCircle,
    className: "bg-verdict-avoid/15 text-verdict-avoid border-verdict-avoid/30",
  },
};

export function VerdictBadge({ verdict, confidence }: { verdict: Verdict; confidence: number }) {
  const meta = VERDICT_META[verdict];
  const Icon = meta.icon;
  return (
    <div className={cn("inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold", meta.className)}>
      <Icon className="h-4 w-4" aria-hidden />
      {meta.label}
      <span className="font-normal opacity-80">- {Math.round(confidence * 100)}% confidence</span>
    </div>
  );
}
