"use client";

import type { EvidenceSummaryItem, InvestigationDetail } from "@/types/investigation";

const MAX_SIGNALS = 5;

/** Compact "why this verdict" list - the same evidence_summary the
 * Evidence Fusion Engine already produces, just capped to the handful of
 * signals that matter most instead of a full technical dump. The
 * complete evidence set is still available in "Evidence & Sources". */
export function WhySummary({ investigation }: { investigation: InvestigationDetail }) {
  const items = investigation.purchase_intelligence?.evidence_summary;
  if (!items || items.length === 0) return null;

  const picked = pickTopSignals(items);
  if (picked.length === 0) return null;

  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <h3 className="mb-3 text-sm font-semibold text-foreground">Why?</h3>
      <ul className="flex flex-col gap-2">
        {picked.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-foreground">
            <span className="mt-0.5 shrink-0 font-mono" aria-hidden>
              {item.icon}
            </span>
            <span>{item.text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function pickTopSignals(items: EvidenceSummaryItem[]): EvidenceSummaryItem[] {
  const contradicts = items.filter((i) => i.type === "contradicts");
  const supports = items.filter((i) => i.type === "supports");
  const neutral = items.filter((i) => i.type === "neutral");
  // Concerns lead (they matter most for a purchase decision), then the
  // strongest positive signals, filling up to MAX_SIGNALS.
  return [...contradicts, ...supports, ...neutral].slice(0, MAX_SIGNALS);
}
