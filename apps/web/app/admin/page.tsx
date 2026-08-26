"use client";

import { AlertTriangle, CheckCircle2, ShieldAlert, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { useFailedInvestigations, useMetricsOverview, useModerationQueue, useResolveReport } from "@/hooks/use-admin";

export default function AdminPage() {
  const { user, isLoading: authLoading } = useAuth();
  const isAdmin = Boolean(user?.is_admin || user?.is_moderator);

  const { data: metrics } = useMetricsOverview(isAdmin);
  const { data: failures } = useFailedInvestigations(isAdmin);
  const { data: queue } = useModerationQueue(isAdmin);
  const { mutate: resolve, isPending: isResolving } = useResolveReport();

  if (authLoading) return null;

  if (!isAdmin) {
    return (
      <div className="container flex flex-col items-center gap-2 py-20 text-center">
        <ShieldAlert className="h-8 w-8 text-muted-foreground" aria-hidden />
        <p className="font-medium">Admin access required</p>
        <p className="text-sm text-muted-foreground">This page is restricted to TrustBuy moderators and admins.</p>
      </div>
    );
  }

  return (
    <div className="container flex flex-col gap-8 py-10">
      <h1 className="text-2xl font-semibold tracking-tight">Admin Dashboard</h1>

      <div className="grid gap-4 sm:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">{metrics?.investigations_today ?? "-"}</CardTitle>
            <CardDescription>Investigations today</CardDescription>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">{metrics?.investigations_total ?? "-"}</CardTitle>
            <CardDescription>Total investigations</CardDescription>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">
              {metrics ? `${Math.round(metrics.average_confidence * 100)}%` : "-"}
            </CardTitle>
            <CardDescription>Average confidence</CardDescription>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">
              {metrics ? `${Math.round(metrics.agent_failure_rate * 100)}%` : "-"}
            </CardTitle>
            <CardDescription>Agent failure rate</CardDescription>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Moderation Queue</CardTitle>
          <CardDescription>Reports pending community or admin resolution, oldest first.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col divide-y divide-border p-0">
          {(queue?.length ?? 0) === 0 && <p className="p-6 text-sm text-muted-foreground">Nothing in the queue.</p>}
          {queue?.map((report) => (
            <div key={report.id} className="flex items-center justify-between gap-4 px-6 py-4">
              <div>
                <Badge variant="outline">{report.report_type}</Badge>
                <p className="mt-1 max-w-md text-sm">{report.description}</p>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={isResolving}
                  onClick={() => resolve({ reportId: report.id, outcome: "confirms" })}
                >
                  <CheckCircle2 className="h-4 w-4" /> Verify
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={isResolving}
                  onClick={() => resolve({ reportId: report.id, outcome: "disputes" })}
                >
                  <XCircle className="h-4 w-4" /> Reject
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center gap-2 space-y-0">
          <AlertTriangle className="h-4 w-4 text-destructive" aria-hidden />
          <CardTitle className="text-base">Failed Investigations</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col divide-y divide-border p-0">
          {(failures?.length ?? 0) === 0 && <p className="p-6 text-sm text-muted-foreground">No recent failures.</p>}
          {failures?.map((f) => (
            <div key={f.investigation_id} className="flex items-center justify-between gap-4 px-6 py-4 text-sm">
              <span className="truncate">{f.source_url}</span>
              <Badge variant="avoid">{f.status}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
