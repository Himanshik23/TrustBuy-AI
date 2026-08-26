"use client";

// Purely decorative ambient background: gradient mesh, blurred blobs, and
// drifting particles. Absolutely positioned + `pointer-events-none` so it
// never interferes with layout or interaction, and every animation here
// is CSS (`animate-*` utilities from tailwind.config.ts) rather than
// JS-driven, so it costs nothing on the main thread and is automatically
// paused by browsers when off-screen. `motion-safe:` gates every
// animation class so `prefers-reduced-motion: reduce` gets a static,
// still-beautiful background instead of forcing motion on someone who
// asked not to see it.

const PARTICLES = [
  { left: "6%", delay: "0s", duration: "8s", size: 3 },
  { left: "14%", delay: "1.2s", duration: "10s", size: 2 },
  { left: "22%", delay: "2.4s", duration: "9s", size: 4 },
  { left: "31%", delay: "0.6s", duration: "11s", size: 2 },
  { left: "40%", delay: "3s", duration: "8.5s", size: 3 },
  { left: "49%", delay: "1.8s", duration: "9.5s", size: 2 },
  { left: "58%", delay: "0.3s", duration: "10.5s", size: 3 },
  { left: "67%", delay: "2.1s", duration: "8s", size: 4 },
  { left: "76%", delay: "1.5s", duration: "9s", size: 2 },
  { left: "85%", delay: "3.4s", duration: "11s", size: 3 },
  { left: "92%", delay: "0.9s", duration: "10s", size: 2 },
  { left: "10%", delay: "4.2s", duration: "9.5s", size: 2 },
  { left: "63%", delay: "4.8s", duration: "8.5s", size: 3 },
  { left: "37%", delay: "5.4s", duration: "10s", size: 2 },
  { left: "80%", delay: "5.9s", duration: "9s", size: 3 },
];

export function BackgroundFX({ className = "" }: { className?: string }) {
  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`} aria-hidden>
      {/* Gradient mesh */}
      <div
        className="absolute inset-0 opacity-70 dark:opacity-60"
        style={{
          background:
            "radial-gradient(60% 50% at 20% 20%, hsl(var(--primary) / 0.16), transparent 60%)," +
            "radial-gradient(50% 45% at 85% 15%, hsl(var(--verdict-buy) / 0.12), transparent 60%)," +
            "radial-gradient(55% 50% at 75% 85%, hsl(var(--primary) / 0.14), transparent 60%)",
        }}
      />

      {/* Blurred blobs */}
      <div className="motion-safe:animate-blob-move absolute -left-24 top-0 h-72 w-72 rounded-full bg-primary/25 blur-3xl sm:h-96 sm:w-96" />
      <div
        className="motion-safe:animate-blob-move absolute -right-16 top-24 h-64 w-64 rounded-full bg-verdict-buy/20 blur-3xl sm:h-80 sm:w-80"
        style={{ animationDelay: "3s" }}
      />
      <div
        className="motion-safe:animate-blob-move absolute bottom-0 left-1/3 h-72 w-72 rounded-full bg-primary/15 blur-3xl sm:h-96 sm:w-96"
        style={{ animationDelay: "6s" }}
      />

      {/* Drifting particles */}
      {PARTICLES.map((p, i) => (
        <span
          key={i}
          className="motion-safe:animate-particle-drift absolute bottom-0 rounded-full bg-primary/50"
          style={{
            left: p.left,
            width: p.size,
            height: p.size,
            animationDelay: p.delay,
            animationDuration: p.duration,
          }}
        />
      ))}

      {/* Subtle grid, fades toward the edges */}
      <div
        className="absolute inset-0 opacity-[0.07] dark:opacity-[0.1]"
        style={{
          backgroundImage:
            "linear-gradient(hsl(var(--foreground)) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--foreground)) 1px, transparent 1px)",
          backgroundSize: "44px 44px",
          maskImage: "radial-gradient(70% 70% at 50% 30%, black, transparent)",
          WebkitMaskImage: "radial-gradient(70% 70% at 50% 30%, black, transparent)",
        }}
      />
    </div>
  );
}
