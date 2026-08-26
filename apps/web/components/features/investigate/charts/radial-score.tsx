"use client";

import { PolarAngleAxis, RadialBar, RadialBarChart } from "recharts";

/** Shared circular gauge for any 0-100 score in the investigation report
 * (verdict confidence, seller trust/transparency, review authenticity,
 * buyer regret). Purely presentational - renders whatever numeric value
 * it's given, never computes or fabricates one. When value is null it
 * shows the same "unavailable" wording the rest of the report already
 * uses instead of a fake 0. */

export type ScoreTone = "buy" | "caution" | "avoid" | "neutral";

const TONE_COLOR: Record<ScoreTone, string> = {
  buy: "hsl(var(--verdict-buy))",
  caution: "hsl(var(--verdict-caution))",
  avoid: "hsl(var(--verdict-avoid))",
  neutral: "hsl(var(--muted-foreground))",
};

const SIZES = { sm: 84, md: 116, lg: 156 } as const;

function autoTone(value: number, invert: boolean): ScoreTone {
  const v = invert ? 100 - value : value;
  if (v >= 70) return "buy";
  if (v >= 40) return "caution";
  return "avoid";
}

export function RadialScore({
  value,
  label,
  sublabel,
  tone,
  invert = false,
  size = "md",
  suffix = "",
  unavailableText = "Data unavailable",
}: {
  value: number | null;
  label: string;
  sublabel?: string;
  tone?: ScoreTone;
  /** Set true when a higher number is worse (e.g. regret probability). */
  invert?: boolean;
  size?: "sm" | "md" | "lg";
  suffix?: string;
  unavailableText?: string;
}) {
  const dim = SIZES[size];

  if (value == null) {
    return (
      <div className="flex flex-col items-center gap-1.5" style={{ width: dim }}>
        <div
          className="flex items-center justify-center rounded-full border border-dashed border-border p-2 text-center text-[10px] leading-tight text-muted-foreground"
          style={{ width: dim, height: dim }}
        >
          {unavailableText}
        </div>
        <span className="text-center text-xs font-medium text-foreground">{label}</span>
      </div>
    );
  }

  const clamped = Math.max(0, Math.min(100, value));
  const resolvedTone = tone ?? autoTone(clamped, invert);
  const color = TONE_COLOR[resolvedTone];
  const data = [{ value: clamped, fill: color }];

  return (
    <div className="flex flex-col items-center gap-1.5" style={{ width: dim }}>
      <div className="relative shrink-0" style={{ width: dim, height: dim }}>
        <RadialBarChart
          width={dim}
          height={dim}
          cx="50%"
          cy="50%"
          innerRadius="74%"
          outerRadius="100%"
          barSize={Math.round(dim * 0.13)}
          data={data}
          startAngle={90}
          endAngle={-270}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} angleAxisId={0} />
          <RadialBar
            dataKey="value"
            background={{ fill: "hsl(var(--border))" }}
            cornerRadius={dim}
            isAnimationActive
            animationDuration={800}
          />
        </RadialBarChart>
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <span className="font-bold text-foreground" style={{ fontSize: Math.round(dim * 0.2) }}>
            {Math.round(clamped)}
            <span className="text-[0.6em] font-semibold opacity-70">{suffix}</span>
          </span>
        </div>
      </div>
      <div className="text-center">
        <span className="block text-xs font-medium text-foreground">{label}</span>
        {sublabel && <span className="block text-[10px] text-muted-foreground">{sublabel}</span>}
      </div>
    </div>
  );
}
