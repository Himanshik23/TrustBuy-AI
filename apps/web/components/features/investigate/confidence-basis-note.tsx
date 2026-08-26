import { Info } from "lucide-react";

import { AGENT_LABELS, type AgentSummary } from "@/types/investigation";

/** Explains *why* the confidence number is what it is, using data already
 * on `investigation.agent_summary` - no backend changes. Purely additive:
 * renders nothing when every registered agent actually found evidence, so
 * it never clutters a fully-evidenced result. */
export function ConfidenceBasisNote({ agentSummary }: { agentSummary: AgentSummary[] }) {
  const withData = agentSummary.filter((a) => a.status === "completed");
  const withoutData = agentSummary.filter((a) => a.status !== "completed");

  if (withoutData.length === 0 || agentSummary.length === 0) return null;

  return (
    <div className="flex items-start gap-2 rounded-md border border-border bg-surface-elevated px-3 py-2 text-xs text-muted-foreground">
      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
      <p>
        Based on {withData.length} of {agentSummary.length} checks -{" "}
        {withoutData.map((a) => AGENT_LABELS[a.agent] ?? a.agent).join(", ")} found no data yet for this listing (a
        new seller, no reviews on the page, or no price history to compare). Confidence rises automatically as
        more evidence becomes available, including from repeat investigations of this listing.
      </p>
    </div>
  );
}
