"use client";

import Link from "next/link";
import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

import { useSampleInvestigations } from "@/hooks/use-investigation";
import type { SampleInvestigation, Verdict } from "@/types/investigation";

/** "Try a sample" - links straight to already-completed investigations
 * instead of submitting a new URL, so visitors (and demos) can see a real
 * BUY / BUY WITH CAUTION / AVOID PURCHASE report instantly without
 * depending on a live fetch succeeding. Only ever shows verdicts that
 * genuinely exist in the system - never a placeholder. */

const VERDICT_META: Record<Verdict, { label: string; icon: typeof CheckCircle2; className: string }> = {
  buy: { label: "BUY example", icon: CheckCircle2, className: "border-verdict-buy/30 text-verdict-buy hover:bg-verdict-buy/10" },
  buy_with_caution: {
    label: "CAUTION example",
    icon: AlertTriangle,
    className: "border-verdict-caution/30 text-verdict-caution hover:bg-verdict-caution/10",
  },
  avoid_purchase: {
    label: "AVOID example",
    icon: XCircle,
    className: "border-verdict-avoid/30 text-verdict-avoid hover:bg-verdict-avoid/10",
  },
};

export function SampleInvestigations() {
  const { data: samples } = useSampleInvestigations();

  if (!samples || samples.length === 0) return null;

  return (
    <div className="relative z-10 mt-5 flex flex-col items-center gap-2">
      <span className="text-xs text-muted-foreground">No product link handy? See a real report instantly:</span>
      <div className="flex flex-wrap items-center justify-center gap-2">
        {samples.map((sample) => (
          <SampleChip key={sample.investigation_id} sample={sample} />
        ))}
      </div>
    </div>
  );
}

function SampleChip({ sample }: { sample: SampleInvestigation }) {
  const meta = VERDICT_META[sample.verdict];
  const Icon = meta.icon;
  return (
    <Link
      href={`/investigate/${sample.investigation_id}`}
      className={`inline-flex items-center gap-1.5 rounded-full border bg-surface/60 px-3 py-1.5 text-xs font-medium backdrop-blur transition-colors ${meta.className}`}
      title={sample.product_title}
    >
      <Icon className="h-3.5 w-3.5" aria-hidden />
      {meta.label}
    </Link>
  );
}
