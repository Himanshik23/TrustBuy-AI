"use client";

import * as React from "react";
import { Download, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { exportInvestigationReport } from "@/lib/api/investigations";

export function ExportReportButton({ investigationId }: { investigationId: string }) {
  const [isExporting, setIsExporting] = React.useState(false);

  async function handleExport() {
    setIsExporting(true);
    try {
      const blob = await exportInvestigationReport(investigationId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `trustbuy-report-${investigationId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <Button variant="outline" size="sm" onClick={handleExport} disabled={isExporting}>
      {isExporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
      Export report
    </Button>
  );
}
