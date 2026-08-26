"use client";

import { RadialScore } from "@/components/features/investigate/charts/radial-score";
import type { PriceIntelligenceData } from "@/types/investigation";

/** Compact Price tab content - surfaces `purchase_intelligence.price_intelligence`,
 * which the Context-Aware Price Intelligence logic already computes but
 * previously had nowhere to render. Read-only presentation; no pricing
 * logic here. */
export function PriceSummary({
  data,
  currency,
}: {
  data: PriceIntelligenceData | null | undefined;
  /** The product's actual currency (ProductSummary.currency) - preferred
   * over `data.currency`, which the backend's price-fairness computation
   * defaults to "USD" whenever it wasn't threaded through. */
  currency?: string;
}) {
  if (!data || data.current_price == null) {
    return <p className="text-sm text-muted-foreground">Insufficient pricing evidence.</p>;
  }
  const displayCurrency = currency || data.currency;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-6">
        <RadialScore value={data.fairness_score} label="Price Fairness" size="md" unavailableText="Insufficient evidence" />
        <div className="flex flex-col gap-1 text-sm">
          <Field label="Current price" value={`${displayCurrency} ${data.current_price.toFixed(2)}`} />
          {data.list_price != null && <Field label="List / MRP" value={`${displayCurrency} ${data.list_price.toFixed(2)}`} />}
          {data.discount_percent != null && <Field label="Discount" value={`${data.discount_percent}%`} />}
        </div>
      </div>
      {data.unrealistic_discount_detected && (
        <p className="text-sm text-verdict-caution">
          This discount was flagged as significantly larger than what TrustBuy&apos;s price history and sale-context
          checks could confirm - worth a second look before buying.
        </p>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground">{value}</span>
    </div>
  );
}
