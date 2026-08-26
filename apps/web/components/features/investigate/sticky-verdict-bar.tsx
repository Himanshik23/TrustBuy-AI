"use client";

import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

import { VerdictBadge } from "@/components/features/investigate/verdict-badge";
import type { Verdict } from "@/types/investigation";

/** Slim bar fixed below the navbar once the main verdict card has
 * scrolled out of view, so the headline result stays visible while
 * skimming a long report. Purely presentational - mirrors whatever
 * verdict/confidence it's given, never recomputes anything. */
export function StickyVerdictBar({
  anchorRef,
  verdict,
  confidence,
  title,
}: {
  anchorRef: React.RefObject<HTMLElement | null>;
  verdict: Verdict;
  confidence: number;
  title: string;
}) {
  const [visible, setVisible] = React.useState(false);
  const reduce = useReducedMotion();

  React.useEffect(() => {
    const el = anchorRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        // Only surface once the anchor has scrolled above the viewport -
        // not before the user has scrolled down to reach it at all.
        setVisible(!entry.isIntersecting && entry.boundingClientRect.top < 0);
      },
      { threshold: 0 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [anchorRef]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={reduce ? undefined : { y: -16, opacity: 0 }}
          animate={reduce ? undefined : { y: 0, opacity: 1 }}
          exit={reduce ? undefined : { y: -16, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-x-0 top-16 z-30 border-b border-border bg-background/95 shadow-sm backdrop-blur"
        >
          <div className="container flex items-center justify-between gap-3 py-2.5">
            <span className="truncate text-sm font-medium text-muted-foreground">{title}</span>
            <VerdictBadge verdict={verdict} confidence={confidence} />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
