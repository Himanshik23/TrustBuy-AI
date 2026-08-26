"use client";

import { ThumbsDown, ThumbsUp } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { useReports, useVoteReport } from "@/hooks/use-community";
import { REPORT_TYPE_LABELS, type ReportStatus } from "@/types/community";

const STATUS_VARIANT: Record<ReportStatus, "buy" | "caution" | "avoid" | "outline" | "secondary"> = {
  verified: "avoid",
  under_review: "caution",
  pending: "outline",
  rejected: "secondary",
  duplicate: "secondary",
};

export function ReportsList({ productId }: { productId: string }) {
  const { user } = useAuth();
  const { data: reports, isLoading } = useReports({ product_id: productId });
  const { mutate: vote } = useVoteReport();

  if (isLoading) return null;
  if (!reports || reports.length === 0) {
    return <p className="text-sm text-muted-foreground">No community reports for this product yet.</p>;
  }

  return (
    <ul className="flex flex-col divide-y divide-border">
      {reports.map((report) => (
        <li key={report.id} className="flex items-start justify-between gap-4 py-3">
          <div className="flex-1">
            <div className="mb-1 flex items-center gap-2">
              <Badge variant={STATUS_VARIANT[report.status]}>{report.status.replace("_", " ")}</Badge>
              <span className="text-xs text-muted-foreground">{REPORT_TYPE_LABELS[report.report_type]}</span>
            </div>
            <p className="text-sm">{report.description}</p>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              disabled={!user}
              onClick={() => vote({ reportId: report.id, vote: 1 })}
              aria-label="Upvote"
            >
              <ThumbsUp className="h-4 w-4" />
            </Button>
            <span className="w-4 text-center text-xs text-muted-foreground">{report.upvotes - report.downvotes}</span>
            <Button
              variant="ghost"
              size="icon"
              disabled={!user}
              onClick={() => vote({ reportId: report.id, vote: -1 })}
              aria-label="Downvote"
            >
              <ThumbsDown className="h-4 w-4" />
            </Button>
          </div>
        </li>
      ))}
    </ul>
  );
}
