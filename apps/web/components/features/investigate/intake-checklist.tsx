import { Check, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

/** Smart URL Intake Pipeline (Feature 1) status - purely additive to the
 * existing investigation page. `POST /investigations` (see
 * services/catalog-service/app/intake.py) normalizes the URL and rejects
 * only clearly malformed input before the Investigation row is created -
 * it no longer fetches the page up front (DECISIONS.md ADR-013), so
 * `detected_platform` is filled in once the investigation's own fetch
 * succeeds, not at creation time. While that's still in flight, this
 * shows an honest "detecting" state instead of a checkmark it hasn't
 * earned yet. */
export function IntakeChecklist({
  detectedPlatform,
  status,
}: {
  detectedPlatform: string | null;
  status: "processing" | "completed" | "failed";
}) {
  const platformKnown = Boolean(detectedPlatform) || status === "completed";

  const items = [
    { label: "Valid URL", done: true },
    {
      label: detectedPlatform ? `Platform detected: ${detectedPlatform}` : "Detecting platform...",
      done: platformKnown,
    },
    { label: "Product page verified", done: platformKnown },
    { label: "Ready for analysis", done: true },
  ];

  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
      {items.map((item) => (
        <li key={item.label} className={cn("flex items-center gap-1.5")}>
          {item.done ? (
            <Check className="h-3.5 w-3.5 text-verdict-buy" aria-hidden />
          ) : (
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
          )}
          {item.label}
        </li>
      ))}
    </ul>
  );
}
