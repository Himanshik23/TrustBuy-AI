"use client";

import { Instagram, Shirt, ShoppingBag, ShoppingCart, Sparkles, Store, Watch, Zap } from "lucide-react";

import { Reveal } from "@/components/features/landing/reveal";

const PLATFORMS = [
  { icon: ShoppingCart, name: "Amazon" },
  { icon: ShoppingBag, name: "Flipkart" },
  { icon: Shirt, name: "Myntra" },
  { icon: Zap, name: "Nike" },
  { icon: Watch, name: "Adidas" },
  { icon: Sparkles, name: "Apple" },
  { icon: Instagram, name: "Instagram Shops" },
  { icon: Store, name: "Independent Stores" },
];

export function PlatformsSection() {
  return (
    <section className="container flex flex-col items-center gap-3 px-4 sm:px-6 py-12 sm:py-24 text-center">
      <Reveal>
        <span className="text-xs font-medium uppercase tracking-wider text-primary">Coverage</span>
      </Reveal>
      <Reveal delay={0.05}>
        <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Supported Platforms</h2>
      </Reveal>
      <Reveal delay={0.08}>
        <p className="max-w-xl text-balance text-muted-foreground">
          Marketplace-agnostic by design - pluggable adapters mean more platforms every release.
        </p>
      </Reveal>

      <div className="mt-8 grid w-full grid-cols-2 gap-3 sm:grid-cols-4">
        {PLATFORMS.map(({ icon: Icon, name }, i) => (
          <Reveal key={name} delay={i * 0.04}>
            <div className="group flex flex-col items-center gap-2.5 rounded-2xl border border-border/60 bg-surface/70 p-5 shadow-sm backdrop-blur-xl transition-all duration-300 hover:-translate-y-1 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/10">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary transition-transform duration-300 group-hover:scale-110">
                <Icon className="h-5 w-5" aria-hidden />
              </span>
              <p className="text-sm font-medium">{name}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
