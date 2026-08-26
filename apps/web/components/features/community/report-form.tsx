"use client";

import * as React from "react";
import axios from "axios";
import { Flag } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/use-auth";
import { useCreateReport } from "@/hooks/use-community";
import { REPORT_TYPE_LABELS, type ReportType } from "@/types/community";
import type { ApiErrorBody } from "@/types/auth";

const REPORT_TYPES = Object.keys(REPORT_TYPE_LABELS) as ReportType[];

export function ReportForm({ productId }: { productId: string }) {
  const { user } = useAuth();
  const [open, setOpen] = React.useState(false);
  const [reportType, setReportType] = React.useState<ReportType>("counterfeit_product");
  const [description, setDescription] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState(false);
  const { mutateAsync, isPending } = useCreateReport();

  if (!user) {
    return (
      <p className="text-sm text-muted-foreground">
        <a href="/login" className="text-primary hover:underline">
          Sign in
        </a>{" "}
        to report an issue with this listing.
      </p>
    );
  }

  if (!open) {
    return (
      <Button variant="outline" onClick={() => setOpen(true)}>
        <Flag className="h-4 w-4" /> Report an issue
      </Button>
    );
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (description.trim().length < 10) {
      setError("Please describe the issue in at least 10 characters.");
      return;
    }
    try {
      await mutateAsync({ report_type: reportType, description: description.trim(), product_id: productId });
      setSuccess(true);
      setDescription("");
    } catch (err) {
      const message =
        (axios.isAxiosError(err) && (err.response?.data as ApiErrorBody | undefined)?.error?.message) ||
        "Could not submit the report. Please try again.";
      setError(message);
    }
  }

  if (success) {
    return (
      <Card className="border-verdict-buy/30">
        <CardContent className="py-6 text-sm">
          Thanks - your report has been submitted for community review. Verified reports earn you Trust Points.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Report an issue with this listing</CardTitle>
        <CardDescription>Help other shoppers by sharing what you found.</CardDescription>
      </CardHeader>
      <form onSubmit={onSubmit}>
        <CardContent className="flex flex-col gap-4">
          {error && (
            <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}
          <div className="flex flex-col gap-2">
            <Label htmlFor="report-type">Type</Label>
            <select
              id="report-type"
              value={reportType}
              onChange={(e) => setReportType(e.target.value as ReportType)}
              className="h-10 rounded-md border border-input bg-surface px-3 text-sm"
            >
              {REPORT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {REPORT_TYPE_LABELS[type]}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="description">Description</Label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              className="rounded-md border border-input bg-surface px-3 py-2 text-sm"
              placeholder="What happened? Include as much detail as you can."
            />
          </div>
        </CardContent>
        <CardFooter className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button type="submit" disabled={isPending}>
            {isPending ? "Submitting..." : "Submit report"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
