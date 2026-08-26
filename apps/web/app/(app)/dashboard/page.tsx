"use client";

import Link from "next/link";
import { Award, Search, ShieldCheck, Trophy } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { UrlSubmitForm } from "@/components/features/investigate/url-submit-form";
import { useAuth } from "@/hooks/use-auth";
import { useMyBadges } from "@/hooks/use-community";
import { useMyInvestigations } from "@/hooks/use-investigation";

const REPUTATION_LABEL: Record<string, string> = {
  shopper: "Shopper",
  investigator: "Investigator",
  fraud_hunter: "Fraud Hunter",
  trust_guardian: "Trust Guardian",
  trust_ambassador: "Trust Ambassador",
};

const STATUS_LABEL: Record<string, string> = {
  processing: "In progress",
  completed: "Completed",
  failed: "Failed",
};

export default function DashboardPage() {
  const { user } = useAuth();
  const { data: investigations, isLoading } = useMyInvestigations(Boolean(user));
  const { data: badges } = useMyBadges(Boolean(user));
  if (!user) return null;

  return (
    <div className="container flex flex-col gap-8 py-10">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Welcome back, {user.display_name}</h1>
        <p className="text-muted-foreground">Paste a product link below to start a new investigation.</p>
      </div>

      <UrlSubmitForm />

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="flex-row items-center gap-3 space-y-0">
            <Trophy className="h-5 w-5 text-primary" aria-hidden />
            <div>
              <CardTitle className="text-base">{user.trust_points} Trust Points</CardTitle>
              <CardDescription>
                <Badge variant="secondary">{REPUTATION_LABEL[user.reputation_level] ?? user.reputation_level}</Badge>
              </CardDescription>
            </div>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center gap-3 space-y-0">
            <ShieldCheck className="h-5 w-5 text-primary" aria-hidden />
            <div>
              <CardTitle className="text-base">Account secured</CardTitle>
              <CardDescription>{user.email}</CardDescription>
            </div>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center gap-3 space-y-0">
            <Search className="h-5 w-5 text-primary" aria-hidden />
            <div>
              <CardTitle className="text-base">{investigations?.length ?? 0} Investigations</CardTitle>
              <CardDescription>Total run so far</CardDescription>
            </div>
          </CardHeader>
        </Card>
      </div>

      {badges && badges.length > 0 && (
        <Card>
          <CardHeader className="flex-row items-center gap-2 space-y-0">
            <Award className="h-4 w-4 text-primary" aria-hidden />
            <CardTitle className="text-base">Your badges</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {badges.map((badge) => (
              <Badge key={badge.code} variant="secondary" title={badge.description ?? undefined}>
                {badge.name}
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent investigations</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col divide-y divide-border p-0">
          {isLoading && <p className="p-6 text-sm text-muted-foreground">Loading...</p>}
          {!isLoading && (investigations?.length ?? 0) === 0 && (
            <div className="flex flex-col items-center gap-2 py-16 text-center text-muted-foreground">
              <Search className="h-8 w-8" aria-hidden />
              <p className="font-medium text-foreground">No investigations yet</p>
              <p className="max-w-sm text-sm">Paste a product URL above to run your first investigation.</p>
            </div>
          )}
          {investigations?.map((inv) => (
            <Link
              key={inv.investigation_id}
              href={`/investigate/${inv.investigation_id}`}
              className="flex items-center justify-between gap-4 px-6 py-4 text-sm hover:bg-secondary"
            >
              <span className="truncate text-foreground">{inv.source_url}</span>
              <Badge variant={inv.status === "failed" ? "avoid" : inv.status === "completed" ? "buy" : "outline"}>
                {STATUS_LABEL[inv.status] ?? inv.status}
              </Badge>
            </Link>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
