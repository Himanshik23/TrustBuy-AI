"use client";

import { Bar, BarChart, Cell, ResponsiveContainer, XAxis, YAxis } from "recharts";

import { AGENT_LABELS, ALL_AGENTS, type AgentSummary } from "@/types/investigation";

/** Horizontal bar comparison of each intelligence agent's confidence -
 * sits alongside (not instead of) the existing AgentProgressList, which
 * still carries the per-agent status text. Renders 0 for any agent that
 * hasn't completed yet rather than guessing a value. */

function toneFor(run: AgentSummary | undefined): string {
  if (!run || run.status !== "completed") return "hsl(var(--border))";
  if (run.verdict_signal === "supports_avoid") return "hsl(var(--verdict-avoid))";
  if (run.verdict_signal === "supports_buy") return "hsl(var(--verdict-buy))";
  return "hsl(var(--verdict-caution))";
}

export function AgentConfidenceChart({ agentSummary }: { agentSummary: AgentSummary[] }) {
  const byName = new Map(agentSummary.map((a) => [a.agent, a]));
  const data = ALL_AGENTS.map((key) => {
    const run = byName.get(key);
    return {
      name: AGENT_LABELS[key] ?? key,
      value: run && run.status === "completed" ? Math.round(run.confidence * 100) : 0,
      fill: toneFor(run),
    };
  });

  if (data.every((d) => d.value === 0)) return null;

  return (
    <div style={{ width: "100%", height: 40 * data.length }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 28, bottom: 4, left: 4 }}>
          <XAxis type="number" domain={[0, 100]} hide />
          <YAxis
            type="category"
            dataKey="name"
            width={132}
            tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
            axisLine={false}
            tickLine={false}
          />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={14} isAnimationActive animationDuration={800}>
            {data.map((d) => (
              <Cell key={d.name} fill={d.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
