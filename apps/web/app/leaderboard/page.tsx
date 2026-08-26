"use client";

import { Trophy } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useLeaderboard } from "@/hooks/use-community";

const REPUTATION_LABEL: Record<string, string> = {
  shopper: "Shopper",
  investigator: "Investigator",
  fraud_hunter: "Fraud Hunter",
  trust_guardian: "Trust Guardian",
  trust_ambassador: "Trust Ambassador",
};

export default function LeaderboardPage() {
  const { data: entries, isLoading } = useLeaderboard();

  return (
    <div className="container max-w-2xl px-4 sm:px-6 py-6 sm:py-10">
      <div className="mb-6 flex items-center gap-2">
        <Trophy className="h-5 w-5 text-primary" aria-hidden />
        <h1 className="text-2xl font-semibold tracking-tight">Community Leaderboard</h1>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Top contributors</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col divide-y divide-border p-0">
          {isLoading && <p className="p-6 text-sm text-muted-foreground">Loading...</p>}
          {entries?.map((entry, index) => (
            <div key={entry.id} className="flex items-center justify-between gap-3 px-4 sm:px-6 py-4">
              <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                <span className="w-5 text-sm font-medium text-muted-foreground sm:w-6">#{index + 1}</span>
                <span className="text-sm font-medium text-foreground">{entry.display_name}</span>
                <Badge variant="secondary" className="text-xs">
                  {REPUTATION_LABEL[entry.reputation_level] ?? entry.reputation_level}
                </Badge>
              </div>
              <span className="shrink-0 text-sm font-semibold">{entry.trust_points} pts</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
