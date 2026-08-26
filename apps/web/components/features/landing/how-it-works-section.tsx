"use client";

import { ArrowDown, ArrowRight, Fingerprint, Link2, ScanSearch, ShieldCheck } from "lucide-react";

import { Reveal } from "@/components/features/landing/reveal";

const STEPS = [
  { icon: Link2, title: "Paste Product URL", description: "Drop in any shopping link - marketplace, brand site, or social store." },
  { icon: ScanSearch, title: "AI Investigates", description: "Platform, seller, review, and price intelligence engines run in parallel." },
  { icon: Fingerprint, title: "Evidence Collection", description: "Every signal is logged and weighted - never a black-box guess." },
  { icon: ShieldCheck, title: "Purchase Recommendation", description: "One explainable verdict: BUY, BUY WITH CAUTION, or AVOID." },
];

export function HowItWorksSection() {
  return (
    <section className="container flex flex-col items-center gap-3 px-4 sm:px-6 py-12 sm:py-24 text-center">
      <Reveal>
        <span className="text-xs font-medium uppercase tracking-wider text-primary">How it works</span>
      </Reveal>
      <Reveal delay={0.05}>
        <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">How TrustBuy AI Works</h2>
      </Reveal>

      <div className="mt-10 flex w-full flex-col items-stretch gap-3 lg:flex-row lg:items-center lg:gap-0">
        {STEPS.map(({ icon: Icon, title, description }, i) => (
          <div key={title} className="flex flex-1 flex-col items-center gap-2 lg:flex-row">
            <Reveal delay={i * 0.1} className="w-full flex-1">
              <div className="group flex h-full flex-col items-center gap-3 rounded-2xl border border-border/60 bg-surface/70 p-6 text-center shadow-sm backdrop-blur-xl transition-all duration-300 hover:-translate-y-1 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/10">
                <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary transition-transform duration-300 group-hover:scale-110">
                  <Icon className="h-6 w-6" aria-hidden />
                </span>
                <p className="text-xs font-medium text-primary">Step {i + 1}</p>
                <h3 className="text-base font-semibold">{title}</h3>
                <p className="text-sm text-muted-foreground">{description}</p>
              </div>
            </Reveal>
            {i < STEPS.length - 1 && (
              <>
                <ArrowRight className="mx-2 hidden h-5 w-5 shrink-0 text-muted-foreground lg:block" aria-hidden />
                <ArrowDown className="block h-5 w-5 shrink-0 text-muted-foreground lg:hidden" aria-hidden />
              </>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
