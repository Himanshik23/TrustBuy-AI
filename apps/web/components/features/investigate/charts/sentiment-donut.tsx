"use client";

import { Cell, Pie, PieChart } from "recharts";

/** Donut visualization for the Positive/Neutral/Negative review sentiment
 * split that Review Intelligence already computes. Purely presentational -
 * renders exactly the three percentages it's handed. */

const COLORS: Record<string, string> = {
  Positive: "hsl(var(--verdict-buy))",
  Neutral: "hsl(var(--muted-foreground))",
  Negative: "hsl(var(--verdict-avoid))",
};

export function SentimentDonut({
  positive,
  neutral,
  negative,
  size = 104,
}: {
  positive: number;
  neutral: number;
  negative: number;
  size?: number;
}) {
  const data = [
    { name: "Positive", value: positive },
    { name: "Neutral", value: neutral },
    { name: "Negative", value: negative },
  ].filter((d) => d.value > 0);

  if (data.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-4">
      <div className="shrink-0" style={{ width: size, height: size }}>
        <PieChart width={size} height={size}>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={Math.round(size * 0.32)}
            outerRadius={Math.round(size * 0.48)}
            paddingAngle={2}
            stroke="none"
            isAnimationActive
            animationDuration={800}
          >
            {data.map((d) => (
              <Cell key={d.name} fill={COLORS[d.name]} />
            ))}
          </Pie>
        </PieChart>
      </div>
      <ul className="flex flex-col gap-1">
        {data.map((d) => (
          <li key={d.name} className="flex items-center gap-1.5 text-xs">
            <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: COLORS[d.name] }} aria-hidden />
            <span className="text-muted-foreground">{d.name}</span>
            <span className="font-semibold text-foreground">{d.value}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
