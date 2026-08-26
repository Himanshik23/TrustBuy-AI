"use client";

import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronDown } from "lucide-react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/** Progressive-disclosure wrapper used to move deep/technical report
 * content out of the main scroll while keeping it one click away -
 * nothing rendered inside is removed, only collapsed by default. */
export function CollapsibleSection({
  title,
  icon: Icon,
  summary,
  defaultOpen = false,
  className,
  children,
}: {
  title: string;
  icon?: React.ComponentType<{ className?: string }>;
  summary?: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = React.useState(defaultOpen);
  const reduce = useReducedMotion();

  return (
    <Card className={className}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-4 rounded-lg p-5 text-left transition-colors hover:bg-secondary/40"
      >
        <div className="flex min-w-0 items-center gap-3">
          {Icon && <Icon className="h-4 w-4 shrink-0 text-primary" aria-hidden />}
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-foreground">{title}</h3>
            {summary && <div className="mt-0.5 truncate text-sm text-muted-foreground">{summary}</div>}
          </div>
        </div>
        <span className="flex shrink-0 items-center gap-2 text-xs font-medium text-primary">
          {open ? "Hide details" : "View details"}
          <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", open && "rotate-180")} aria-hidden />
        </span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={reduce ? undefined : { height: 0, opacity: 0 }}
            animate={reduce ? undefined : { height: "auto", opacity: 1 }}
            exit={reduce ? undefined : { height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 pt-0">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
