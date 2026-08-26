"use client";

import type { SellerProfileData } from "@/types/investigation";

const NOT_APPLICABLE = "Not Applicable";

/** Compact Business tab content - the business-verification fields
 * already present on `seller_profile`, split into their own tab per the
 * report hierarchy. No new data or scoring - purely a different view of
 * fields SellerCommunityIntelligenceSection already has. */
export function BusinessSummary({ seller }: { seller: SellerProfileData | null | undefined }) {
  if (!seller) return null;

  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
      <Field
        label="Business verification"
        value={seller.business_verified == null ? "Data unavailable" : seller.business_verified ? "Verified" : "Not verified"}
      />
      <Field label="GST / company information" value={seller.business_registration_info} />
      <Field label="Privacy Policy" value={seller.privacy_policy} />
      <Field label="Terms & Conditions" value={seller.terms_conditions} />
      <Field label="Secure payment methods" value={seller.secure_payment} />
    </dl>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  const isNotApplicable = value === NOT_APPLICABLE;
  return (
    <div className="flex justify-between gap-3 sm:block">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={`text-right sm:text-left ${isNotApplicable ? "text-muted-foreground" : "text-foreground"}`}>{value}</dd>
    </div>
  );
}
