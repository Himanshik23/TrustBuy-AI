"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Instagram, Percent, ShieldOff, Star, Copy, Fish } from "lucide-react";

import { cn } from "@/lib/utils";
import { Reveal } from "@/components/features/landing/reveal";

const SCAMS = [
  {
    icon: Percent,
    title: "Fake Discounts",
    summary: "\"80% OFF\" prices inflated first, then discounted back to normal.",
    detection: "Price Intelligence compares against historical and cross-store prices to flag unrealistic discounts.",
  },
  {
    icon: Star,
    title: "Fake Reviews",
    summary: "Bulk 5-star reviews with near-identical wording and posting times.",
    detection: "Review Intelligence detects duplicate phrasing, spam patterns, and rating/sentiment mismatches.",
  },
  {
    icon: Copy,
    title: "Counterfeit Products",
    summary: "Unauthorized replicas sold as \"genuine\" on marketplaces or ads.",
    detection: "Seller Intelligence checks official domain ownership and brand-authorization signals.",
  },
  {
    icon: Instagram,
    title: "Fake Instagram Stores",
    summary: "New accounts with stock photos, no reviews, and no return policy.",
    detection: "Platform Classification flags Social Commerce sellers and checks for a verifiable business profile.",
  },
  {
    icon: Fish,
    title: "Phishing Shopping Websites",
    summary: "Lookalike domains built to steal payment details, not ship products.",
    detection: "Platform Verification checks domain trust, HTTPS/SSL validity, and certificate issuers.",
  },
  {
    icon: ShieldOff,
    title: "No Return Policy",
    summary: "No refund or return terms disclosed anywhere on the listing.",
    detection: "Seller Intelligence surfaces missing or restrictive return/refund policies as a risk signal.",
  },
];

export function ScamAwarenessSection() {
  const [openIndex, setOpenIndex] = React.useState<number | null>(null);

  return (
    <section className="container flex flex-col items-center gap-3 py-24 text-center">
      <Reveal>
        <span className="text-xs font-medium uppercase tracking-wider text-primary">Stay alert</span>
      </Reveal>
      <Reveal delay={0.05}>
        <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Common Online Shopping Scams</h2>
      </Reveal>
      <Reveal delay={0.08}>
        <p className="max-w-xl text-balance text-muted-foreground">Tap a card to see how TrustBuy AI catches it.</p>
      </Reveal>

      <div className="mt-8 grid w-full grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SCAMS.map(({ icon: Icon, title, summary, detection }, i) => {
          const open = openIndex === i;
          return (
            <Reveal key={title} delay={i * 0.05}>
              <button
                type="button"
                onClick={() => setOpenIndex(open ? null : i)}
                aria-expanded={open}
                className={cn(
                  "flex h-full w-full flex-col gap-3 rounded-2xl border bg-surface/70 p-6 text-left shadow-sm backdrop-blur-xl transition-all duration-300 hover:-translate-y-1 hover:shadow-lg",
                  open ? "border-primary/50 shadow-primary/10" : "border-border/60 hover:border-primary/30"
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-verdict-avoid/10 text-verdict-avoid">
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                  <ChevronDown className={cn("mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} aria-hidden />
                </div>
                <h3 className="text-base font-semibold">{title}</h3>
                <p className="text-sm text-muted-foreground">{summary}</p>
                <AnimatePresence initial={false}>
                  {open && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25, ease: "easeInOut" }}
                      className="overflow-hidden"
                    >
                      <div className="mt-1 flex items-start gap-2 rounded-lg border border-verdict-buy/20 bg-verdict-buy/5 p-3 text-xs text-foreground">
                        <span className="font-semibold text-verdict-buy">How TrustBuy AI detects it:</span> {detection}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </button>
            </Reveal>
          );
        })}
      </div>
    </section>
  );
}
