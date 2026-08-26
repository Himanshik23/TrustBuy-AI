"use client";

import * as React from "react";
import { animate, useInView, useReducedMotion } from "framer-motion";
import { Layers, Search, ShieldAlert, Store } from "lucide-react";

import { Reveal } from "@/components/features/landing/reveal";

const STATS = [
  { icon: Search, target: 12000, suffix: "+", label: "Products Investigated" },
  { icon: Store, target: 15, suffix: "+", label: "Trusted Platforms Supported" },
  { icon: ShieldAlert, target: 30, suffix: "+", label: "Fraud Indicators Checked" },
  { icon: Layers, target: 9, suffix: "", label: "AI Modules Used" },
];

export function StatsSection() {
  return (
    <section className="relative overflow-hidden py-12 sm:py-24">
      <div
        className="pointer-events-none absolute inset-0 opacity-60 dark:opacity-50"
        style={{ background: "radial-gradient(60% 60% at 50% 40%, hsl(var(--primary) / 0.1), transparent 70%)" }}
        aria-hidden
      />
      <div className="container relative flex flex-col items-center gap-3 px-4 sm:px-6 text-center">
        <Reveal>
          <span className="text-xs font-medium uppercase tracking-wider text-primary">Why users trust us</span>
        </Reveal>
        <Reveal delay={0.05}>
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Why Users Trust TrustBuy AI</h2>
        </Reveal>

        <div className="mt-10 grid w-full grid-cols-2 gap-4 lg:grid-cols-4">
          {STATS.map(({ icon: Icon, target, suffix, label }, i) => (
            <Reveal key={label} delay={i * 0.08}>
              <div className="flex flex-col items-center gap-2 rounded-2xl border border-border/60 bg-surface/70 p-6 shadow-sm backdrop-blur-xl">
                <Icon className="h-5 w-5 text-primary" aria-hidden />
                <StatCounter target={target} suffix={suffix} />
                <p className="text-sm text-muted-foreground">{label}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function StatCounter({ target, suffix }: { target: number; suffix: string }) {
  const ref = React.useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const reduce = useReducedMotion();
  const [value, setValue] = React.useState(reduce ? target : 0);

  React.useEffect(() => {
    if (!inView || reduce) return;
    const controls = animate(0, target, {
      duration: 1.4,
      ease: "easeOut",
      onUpdate: (v) => setValue(Math.round(v)),
    });
    return () => controls.stop();
  }, [inView, reduce, target]);

  return (
    <span ref={ref} className="text-3xl font-semibold tracking-tight text-foreground">
      {value.toLocaleString()}
      {suffix}
    </span>
  );
}
