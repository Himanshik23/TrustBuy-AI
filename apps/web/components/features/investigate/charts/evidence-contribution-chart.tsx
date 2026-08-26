"use client";

import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { EvidenceItemOut } from "@/types/investigation";

/** Visualizes exactly what the Evidence Fusion Engine actually weighed -
 * one bar per evidence item, signed by polarity (supports pushes right/
 * green, contradicts pushes left/red, neutral sits at zero), length is
 * the agent's own `weight` (0-1, already computed - never re-derived
 * here). This is what makes the verdict explainable rather than a black
 * box: every bar traces back to a real evidence row from this
 * investigation. */

const POLARITY_COLOR: Record<string, string> = {
  supports: "hsl(var(--verdict-buy))",
  contradicts: "hsl(var(--verdict-avoid))",
  neutral: "hsl(var(--muted-foreground))",
};

function truncate(text: string, max = 42) {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

export function EvidenceContributionChart({ items }: { items: EvidenceItemOut[] }) {
  const isMobile = typeof window !== "undefined" && window.innerWidth < 640;
  const maxChars = isMobile ? 22 : 42;
  const yWidth = isMobile ? 120 : 200;

  const data = items
    .map((item) => ({
      id: item.id,
      label: truncate(item.summary, maxChars),
      fullText: item.summary,
      polarity: item.polarity,
      // Signed so "contradicts" bars extend left of zero and "supports"
      // bars extend right - a quick visual read of which way the
      // evidence pulled the verdict, and by how much.
      signedWeight: item.polarity === "contradicts" ? -item.weight : item.polarity === "supports" ? item.weight : 0,
    }))
    .sort((a, b) => Math.abs(b.signedWeight) - Math.abs(a.signedWeight));

  if (data.length === 0) return null;

  return (
    <div style={{ width: "100%", height: Math.max(44 * data.length, 88) }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 4 }}>
          <XAxis type="number" domain={[-1, 1]} hide />
          <YAxis
            type="category"
            dataKey="label"
            width={yWidth}
            tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "hsl(var(--secondary))" }}
            formatter={(_value: number, _name: string, item) => [
              `weight ${Math.abs(item.payload.signedWeight).toFixed(2)} · ${item.payload.polarity}`,
              item.payload.fullText,
            ]}
            contentStyle={{
              background: "hsl(var(--surface-elevated))",
              border: "1px solid hsl(var(--border))",
              borderRadius: 8,
              fontSize: 12,
              maxWidth: 280,
            }}
          />
          <Bar dataKey="signedWeight" radius={4} barSize={14} isAnimationActive animationDuration={800}>
            {data.map((d) => (
              <Cell key={d.id} fill={POLARITY_COLOR[d.polarity] ?? POLARITY_COLOR.neutral} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
