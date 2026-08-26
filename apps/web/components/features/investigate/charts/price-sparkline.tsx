"use client";

import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { PriceHistoryPoint } from "@/types/investigation";

/** Price trend sparkline shown next to the product price. Prices only
 * accumulate in `price_history` once TrustBuy has investigated this exact
 * listing more than once (see routes.py's price-history endpoint) - a
 * single data point can't show a trend, so the caller is expected to only
 * render this when there are 2+ points rather than faking a flat line. */

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function PriceSparkline({
  points,
  currency,
}: {
  points: PriceHistoryPoint[];
  currency: string;
}) {
  if (points.length < 2) return null;

  const data = points.map((p) => ({ ...p, label: formatDate(p.recorded_at) }));
  const prices = data.map((d) => d.price);
  const first = prices[0];
  const last = prices[prices.length - 1];
  const trend = last > first ? "up" : last < first ? "down" : "flat";
  const trendColor =
    trend === "up" ? "hsl(var(--verdict-avoid))" : trend === "down" ? "hsl(var(--verdict-buy))" : "hsl(var(--muted-foreground))";
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const pad = Math.max((max - min) * 0.15, 1);

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-medium text-muted-foreground">Price history ({data.length} observations)</span>
        <span className="text-xs font-semibold" style={{ color: trendColor }}>
          {trend === "up" ? "▲ risen" : trend === "down" ? "▼ dropped" : "— steady"} since first seen
        </span>
      </div>
      <div style={{ width: "100%", height: 64 }}>
        <ResponsiveContainer>
          <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
            <defs>
              <linearGradient id="priceSparklineFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={trendColor} stopOpacity={0.35} />
                <stop offset="100%" stopColor={trendColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="label" hide />
            <YAxis domain={[min - pad, max + pad]} hide />
            <Tooltip
              formatter={(value: number) => [`${currency} ${value.toFixed(2)}`, "Price"]}
              labelFormatter={(label) => label}
              contentStyle={{
                background: "hsl(var(--surface-elevated))",
                border: "1px solid hsl(var(--border))",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Area
              type="monotone"
              dataKey="price"
              stroke={trendColor}
              strokeWidth={2}
              fill="url(#priceSparklineFill)"
              isAnimationActive
              animationDuration={800}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
