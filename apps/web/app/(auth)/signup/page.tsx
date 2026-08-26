import type { Metadata } from "next";

import { SignupForm } from "@/components/features/auth/signup-form";

export const metadata: Metadata = { title: "Create your account - TrustBuy AI" };

export default function SignupPage() {
  return <SignupForm />;
}
