import { HeroSection } from "@/components/features/landing/hero-section";
import { HowItWorksSection } from "@/components/features/landing/how-it-works-section";
import { WhyTrustBuySection } from "@/components/features/landing/why-trustbuy-section";
import { ScamAwarenessSection } from "@/components/features/landing/scam-awareness-section";
import { StatsSection } from "@/components/features/landing/stats-section";
import { PlatformsSection } from "@/components/features/landing/platforms-section";
import { CtaSection } from "@/components/features/landing/cta-section";

export default function LandingPage() {
  return (
    <div className="flex flex-col">
      <HeroSection />
      <HowItWorksSection />
      <WhyTrustBuySection />
      <ScamAwarenessSection />
      <StatsSection />
      <PlatformsSection />
      <CtaSection />
    </div>
  );
}
