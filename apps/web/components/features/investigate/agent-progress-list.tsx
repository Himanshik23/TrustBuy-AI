import { AlertCircle, CheckCircle2, CircleDashed, Loader2, MinusCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import { ALL_AGENTS, AGENT_LABELS, type AgentSummary, type InvestigationStatus } from "@/types/investigation";

export function AgentProgressList({
  agentSummary,
  investigationStatus,
}: {
  agentSummary: AgentSummary[];
  investigationStatus: InvestigationStatus;
}) {
  const byName = new Map(agentSummary.map((a) => [a.agent, a]));

  return (
    <ul className="flex flex-col gap-2">
      {ALL_AGENTS.map((agentName, index) => {
        const run = byName.get(agentName);
        const isNextUp = !run && investigationStatus === "processing" && index === agentSummary.length;

        return (
          <li
            key={agentName}
            className="flex items-center justify-between rounded-md border border-border bg-surface px-4 py-3 animate-fade-in"
          >
            <div className="flex items-center gap-3">
              <StatusIcon run={run} isRunning={isNextUp} />
              <span className="text-sm font-medium">{AGENT_LABELS[agentName] ?? agentName}</span>
            </div>
            <StatusLabel run={run} isRunning={isNextUp} />
          </li>
        );
      })}
    </ul>
  );
}

function StatusIcon({ run, isRunning }: { run: AgentSummary | undefined; isRunning: boolean }) {
  if (isRunning) return <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden />;
  if (!run) return <CircleDashed className="h-4 w-4 text-muted-foreground" aria-hidden />;
  if (run.status === "completed") return <CheckCircle2 className="h-4 w-4 text-verdict-buy" aria-hidden />;
  if (run.status === "insufficient_data") return <MinusCircle className="h-4 w-4 text-muted-foreground" aria-hidden />;
  return <AlertCircle className="h-4 w-4 text-verdict-avoid" aria-hidden />;
}

function StatusLabel({ run, isRunning }: { run: AgentSummary | undefined; isRunning: boolean }) {
  if (isRunning) return <span className="text-xs text-muted-foreground">running...</span>;
  if (!run) return <span className="text-xs text-muted-foreground">queued</span>;
  if (run.status === "completed") {
    return (
      <span className={cn("text-xs font-medium", run.verdict_signal === "supports_avoid" ? "text-verdict-avoid" : "text-muted-foreground")}>
        {run.verdict_signal?.replace("supports_", "")} - {Math.round(run.confidence * 100)}%
      </span>
    );
  }
  if (run.status === "insufficient_data") return <span className="text-xs text-muted-foreground">no data yet</span>;
  return <span className="text-xs text-verdict-avoid">{run.status}</span>;
}
