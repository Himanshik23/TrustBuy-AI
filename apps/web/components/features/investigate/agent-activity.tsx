"use client";

import { motion, useReducedMotion } from "framer-motion";
import { AlertCircle, Check, MinusCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import { AGENT_LABELS, ALL_AGENTS, type AgentSummary, type InvestigationStatus } from "@/types/investigation";

/** Visual "AI at work" strip shown while an investigation is running -
 * each of the 4 agents as a node that pulses while active and locks into
 * a colored, checked state once its real result lands. Purely a skin over
 * the same `agentSummary` data AgentProgressList already renders; invents
 * no state of its own. */

type NodeState = "queued" | "active" | "supports" | "avoid" | "neutral" | "failed";

function nodeState(run: AgentSummary | undefined, isActive: boolean): NodeState {
  if (isActive) return "active";
  if (!run) return "queued";
  if (run.status === "completed") {
    if (run.verdict_signal === "supports_avoid") return "avoid";
    if (run.verdict_signal === "supports_buy") return "supports";
    return "neutral";
  }
  if (run.status === "insufficient_data") return "neutral";
  return "failed";
}

const STATE_STYLE: Record<NodeState, string> = {
  queued: "border-dashed border-border bg-surface text-muted-foreground",
  active: "border-primary bg-primary/10 text-primary",
  supports: "border-verdict-buy bg-verdict-buy/15 text-verdict-buy",
  avoid: "border-verdict-avoid bg-verdict-avoid/15 text-verdict-avoid",
  neutral: "border-border bg-secondary text-muted-foreground",
  failed: "border-verdict-avoid bg-verdict-avoid/15 text-verdict-avoid",
};

export function AgentActivity({
  agentSummary,
  investigationStatus,
}: {
  agentSummary: AgentSummary[];
  investigationStatus: InvestigationStatus;
}) {
  const byName = new Map(agentSummary.map((a) => [a.agent, a]));
  const reduce = useReducedMotion();

  return (
    <div className="flex items-start justify-between gap-1 py-2 sm:gap-2">
      {ALL_AGENTS.map((agentName, index) => {
        const run = byName.get(agentName);
        const isActive = !run && investigationStatus === "processing" && index === agentSummary.length;
        const state = nodeState(run, isActive);
        const isLast = index === ALL_AGENTS.length - 1;
        const connectorDone = Boolean(run);

        return (
          <div key={agentName} className="flex flex-1 items-start">
            <div className="flex flex-1 flex-col items-center gap-2 text-center">
              <motion.div
                animate={
                  state === "active" && !reduce
                    ? { scale: [1, 1.12, 1], boxShadow: ["0 0 0 0 hsl(var(--primary)/0.35)", "0 0 0 8px hsl(var(--primary)/0)", "0 0 0 0 hsl(var(--primary)/0)"] }
                    : undefined
                }
                transition={state === "active" ? { duration: 1.6, repeat: Infinity, ease: "easeInOut" } : undefined}
                className={cn(
                  "flex h-11 w-11 shrink-0 items-center justify-center rounded-full border-2 transition-colors sm:h-12 sm:w-12",
                  STATE_STYLE[state]
                )}
              >
                {state === "supports" && <Check className="h-5 w-5" aria-hidden />}
                {state === "avoid" && <AlertCircle className="h-5 w-5" aria-hidden />}
                {state === "failed" && <AlertCircle className="h-5 w-5" aria-hidden />}
                {state === "neutral" && <MinusCircle className="h-5 w-5" aria-hidden />}
                {state === "active" && (
                  <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-primary" aria-hidden />
                )}
                {state === "queued" && <span className="h-2 w-2 rounded-full bg-border" aria-hidden />}
              </motion.div>
              <span className="text-[11px] font-medium leading-tight text-foreground sm:text-xs">
                {AGENT_LABELS[agentName] ?? agentName}
              </span>
              <span className="text-[10px] text-muted-foreground">
                {run
                  ? run.status === "completed"
                    ? `${Math.round(run.confidence * 100)}%`
                    : run.status.replace("_", " ")
                  : isActive
                    ? "running..."
                    : "queued"}
              </span>
            </div>
            {!isLast && (
              <div className="mt-5 h-0.5 flex-1 rounded-full bg-border sm:mt-[1.375rem]">
                <motion.div
                  initial={false}
                  animate={{ width: connectorDone ? "100%" : "0%" }}
                  transition={{ duration: 0.5 }}
                  className="h-0.5 rounded-full bg-primary"
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
