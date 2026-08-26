"use client";

import { BadgeCheck, MessageSquareText, ShieldAlert, Sparkles, Tags, Users } from "lucide-react";

import { Reveal } from "@/components/features/landing/reveal";

const FEATURES = [
  { icon: BadgeCheck, title: "Seller Intelligence", description: "Domain ownership, policies, and trust scoring adapted to the platform type." },
  { icon: MessageSquareText, title: "Review Intelligence", description: "Sentiment, authenticity, and complaint patterns across public reviews." },
  { icon: Tags, title: "Price Intelligence", description: "Cross-store comparison to catch fake discounts before you fall for them." },
  { icon: ShieldAlert, title: "Scam Detection", description: "Fake urgency, counterfeit signals, and phishing patterns flagged automatically." },
  { icon: Users, title: "Community Insights", description: "Verified shopper reports strengthen every future recommendation." },
  { icon: Sparkles, title: "Evidence-based AI", description: "Every verdict cites the evidence behind it - never a bare score." },
];

export function WhyTrustBuySection() {
  return (
    <section className="container flex flex-col items-center gap-3 px-4 sm:px-6 py-12 sm:py-24 text-center">
      <Reveal>
        <span className="text-xs font-medium uppercase tracking-wider text-primary">Why TrustBuy AI</span>
      </Reveal>
      <Reveal delay={0.05}>
        <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Built for real purchase decisions</h2>
      </Reveal>

      <div className="mt-10 grid w-full grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, description }, i) => (
          <Reveal key={title} delay={i * 0.06}>
            <div className="group relative h-full overflow-hidden rounded-2xl border border-border/60 bg-surface/70 p-6 text-left shadow-sm backdrop-blur-xl transition-all duration-300 hover:-translate-y-1.5 hover:border-primary/40 hover:shadow-xl hover:shadow-primary/10">
              <div className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-primary/10 blur-2xl transition-opacity duration-300 group-hover:opacity-100 opacity-0" />
              <span className="relative flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3">
                <Icon className="h-5 w-5" aria-hidden />
              </span>
              <h3 className="relative mt-4 text-base font-semibold">{title}</h3>
              <p className="relative mt-1.5 text-sm text-muted-foreground">{description}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
