"use client";

import { motion, useReducedMotion } from "framer-motion";
import { Sparkles } from "lucide-react";

// The glowing AI orb beside the hero search bar. Framer Motion drives a
// slow float + breathing glow loop - `useReducedMotion` collapses it to a
// static glow when the user has asked the OS for less motion.
export function AiOrb({ className = "" }: { className?: string }) {
  const reduce = useReducedMotion();

  return (
    <motion.div
      className={`relative flex h-16 w-16 shrink-0 items-center justify-center ${className}`}
      animate={reduce ? undefined : { y: [0, -10, 0] }}
      transition={reduce ? undefined : { duration: 4.5, repeat: Infinity, ease: "easeInOut" }}
    >
      <motion.span
        className="absolute inset-0 rounded-full bg-primary/40 blur-xl"
        animate={reduce ? undefined : { opacity: [0.5, 0.9, 0.5], scale: [1, 1.15, 1] }}
        transition={reduce ? undefined : { duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
      />
      <span className="relative flex h-12 w-12 items-center justify-center rounded-full border border-primary/30 bg-gradient-to-br from-primary to-verdict-buy text-primary-foreground shadow-lg shadow-primary/30">
        <Sparkles className="h-5 w-5" aria-hidden />
      </span>
    </motion.div>
  );
}
