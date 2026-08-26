"use client";

import { Sparkles } from "lucide-react";

import { UrlSubmitForm } from "@/components/features/investigate/url-submit-form";
import { BackgroundFX } from "@/components/features/landing/background-fx";
import { Reveal } from "@/components/features/landing/reveal";

export function CtaSection() {
  return (
    <section className="relative overflow-hidden border-y border-border/60 px-4 sm:px-6 py-16 sm:py-28 text-center">
      <BackgroundFX />
      <div className="relative mx-auto flex max-w-2xl flex-col items-center gap-6">
        <Reveal>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-elevated/80 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur">
            <Sparkles className="h-3.5 w-3.5 text-primary" aria-hidden /> Ready when you are
          </span>
        </Reveal>
        <Reveal delay={0.08}>
          <h2 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            Paste any shopping link and let TrustBuy AI investigate before you spend.
          </h2>
        </Reveal>
        <Reveal delay={0.16} className="w-full">
          <div className="w-full rounded-2xl border border-border/60 bg-surface/70 p-2 shadow-2xl shadow-primary/10 backdrop-blur-xl">
            <UrlSubmitForm size="large" />
          </div>
        </Reveal>
      </div>
    </section>
  );
}
