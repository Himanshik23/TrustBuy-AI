"use client";

import * as React from "react";
import { ChevronDown, Minus, ThumbsDown, ThumbsUp } from "lucide-react";

import { cn } from "@/lib/utils";
import type { EvidenceItemOut } from "@/types/investigation";

const POLARITY_META = {
  supports: { icon: ThumbsUp, className: "text-verdict-buy" },
  contradicts: { icon: ThumbsDown, className: "text-verdict-avoid" },
  neutral: { icon: Minus, className: "text-muted-foreground" },
} as const;

export function EvidenceTimeline({ items }: { items: EvidenceItemOut[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">No evidence has been collected for this investigation yet.</p>;
  }

  return (
    <ul className="flex flex-col divide-y divide-border">
      {items.map((item) => (
        <EvidenceRow key={item.id} item={item} />
      ))}
    </ul>
  );
}

function EvidenceRow({ item }: { item: EvidenceItemOut }) {
  const [open, setOpen] = React.useState(false);
  const meta = POLARITY_META[item.polarity] ?? POLARITY_META.neutral;
  const Icon = meta.icon;

  return (
    <li className="py-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-3 text-left"
        aria-expanded={open}
      >
        <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", meta.className)} aria-hidden />
        <span className="flex-1 text-sm">{item.summary}</span>
        <ChevronDown className={cn("mt-0.5 h-4 w-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} aria-hidden />
      </button>
      {open && (
        <pre className="mt-2 overflow-x-auto rounded-md bg-surface-elevated p-3 font-mono text-xs text-muted-foreground">
          {JSON.stringify(item.detail, null, 2)}
        </pre>
      )}
    </li>
  );
}
