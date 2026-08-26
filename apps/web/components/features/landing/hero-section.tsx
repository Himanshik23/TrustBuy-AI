"use client";

import { motion, useReducedMotion } from "framer-motion";
import { ChevronDown, EyeOff, ShieldCheck, Star, Tags } from "lucide-react";

import { UrlSubmitForm } from "@/components/features/investigate/url-submit-form";
import { BackgroundFX } from "@/components/features/landing/background-fx";
import { AiOrb } from "@/components/features/landing/ai-orb";
import { SampleInvestigations } from "@/components/features/landing/sample-investigations";

const HEADLINE_WORDS = ["Know", "Before", "You", "Buy."];

const TRUST_INDICATORS = [
  { icon: ShieldCheck, label: "Detect Fake Sellers" },
  { icon: Star, label: "Analyze Reviews" },
  { icon: Tags, label: "Compare Prices" },
  { icon: EyeOff, label: "Scam Detection" },
];

export function HeroSection() {
  const reduce = useReducedMotion();

  return (
    <section className="relative flex min-h-[85vh] flex-col items-center justify-center overflow-hidden px-4 pb-16 pt-12 sm:px-6 sm:pt-20 text-center">
      <BackgroundFX />

      <motion.span
        initial={reduce ? undefined : { opacity: 0, y: -8 }}
        animate={reduce ? undefined : { opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 mb-5 inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-elevated/80 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur"
      >
        <ShieldCheck className="h-3.5 w-3.5 text-primary" aria-hidden />
        AI Purchase Intelligence Platform
      </motion.span>

      <h1 className="relative z-10 flex max-w-4xl flex-wrap items-center justify-center gap-x-2 text-balance text-3xl font-semibold tracking-tight sm:gap-x-3 sm:text-6xl md:text-7xl">
        {HEADLINE_WORDS.map((word, i) => (
          <motion.span
            key={word}
            initial={reduce ? undefined : { opacity: 0, y: 24 }}
            animate={reduce ? undefined : { opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.15 + i * 0.08, ease: "easeOut" }}
            className={word === "Buy." ? "bg-gradient-to-r from-primary to-verdict-buy bg-clip-text text-transparent" : undefined}
          >
            {word}
          </motion.span>
        ))}
      </h1>

      <motion.p
        initial={reduce ? undefined : { opacity: 0, y: 16 }}
        animate={reduce ? undefined : { opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.5 }}
        className="relative z-10 mt-5 max-w-2xl text-balance text-lg text-muted-foreground sm:text-xl"
      >
        TrustBuy AI investigates the product, the seller, the reviews, and the price before you spend a rupee -
        then gives you one explainable verdict, backed by evidence.
      </motion.p>

      <motion.div
        initial={reduce ? undefined : { opacity: 0, y: 20 }}
        animate={reduce ? undefined : { opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.65 }}
        className="relative z-10 mt-9 flex w-full max-w-2xl flex-col items-center gap-4 sm:flex-row sm:justify-center"
      >
        <AiOrb className="hidden sm:flex" />
        <div className="w-full rounded-2xl border border-border/60 bg-surface/60 p-2 shadow-2xl shadow-primary/10 backdrop-blur-xl transition-shadow hover:shadow-primary/20">
          <UrlSubmitForm size="large" />
        </div>
      </motion.div>

      <SampleInvestigations />

      <motion.div
        initial={reduce ? undefined : { opacity: 0, y: 12 }}
        animate={reduce ? undefined : { opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.85 }}
        className="relative z-10 mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-3"
      >
        {TRUST_INDICATORS.map(({ icon: Icon, label }) => (
          <span key={label} className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <Icon className="h-4 w-4 text-verdict-buy" aria-hidden />
            {label}
          </span>
        ))}
      </motion.div>

      <motion.div
        initial={reduce ? undefined : { opacity: 0 }}
        animate={reduce ? undefined : { opacity: 1 }}
        transition={{ duration: 0.6, delay: 1.05 }}
        className="relative z-10 mt-10 flex flex-col items-center gap-1.5 text-xs text-muted-foreground"
      >
        <span>See how it works</span>
        <motion.span
          animate={reduce ? undefined : { y: [0, 6, 0] }}
          transition={reduce ? undefined : { duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
        >
          <ChevronDown className="h-4 w-4" aria-hidden />
        </motion.span>
      </motion.div>
    </section>
  );
}
