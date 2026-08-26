"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/use-auth";

/** Route-group guard for every authenticated screen - redirects to /login
 * once the silent-refresh boot check (hooks/use-auth.tsx) resolves with no
 * session. Server-side auth guarding is a documented Phase 2 upgrade once
 * there's a session-aware Next.js middleware talking to the gateway. */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  if (isLoading || !user) {
    return (
      <div className="container flex min-h-[calc(100vh-4rem)] items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading your account...</p>
      </div>
    );
  }

  return <>{children}</>;
}
