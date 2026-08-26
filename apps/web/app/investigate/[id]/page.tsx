import type { Metadata } from "next";

import { InvestigationView } from "@/components/features/investigate/investigation-view";

export const metadata: Metadata = { title: "Investigation - TrustBuy AI" };

export default async function InvestigationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="container max-w-3xl px-4 sm:px-6 py-6 sm:py-10">
      <InvestigationView id={id} />
    </div>
  );
}
