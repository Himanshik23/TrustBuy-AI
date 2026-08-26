"use client";

import { Building2, CheckCircle2, ExternalLink, RotateCcw, ShieldCheck, Star } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import type { SellerIntelligenceData } from "@/types/investigation";

export function SellerIntelligenceCard({ data }: { data?: SellerIntelligenceData | null }) {
  if (!data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Building2 className="h-5 w-5 text-muted-foreground" />
            Seller Intelligence
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Data unavailable</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/60 shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Building2 className="h-5 w-5 text-primary" />
            Seller Intelligence
          </CardTitle>
          {data.trust_score !== null ? (
            <Badge variant="outline" className={`px-2.5 py-1 text-xs font-semibold ${data.trust_score >= 70 ? "border-emerald-500/30 text-emerald-600 bg-emerald-500/10" : data.trust_score >= 40 ? "border-amber-500/30 text-amber-600 bg-amber-500/10" : "border-rose-500/30 text-rose-600 bg-rose-500/10"}`}>
              Trust Score: {data.trust_score}%
            </Badge>
          ) : (
            <Badge variant="outline" className="text-xs text-muted-foreground">
              Data unavailable
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="flex flex-col gap-1 p-3 rounded-lg bg-muted/40 border border-border/40">
            <span className="text-xs text-muted-foreground font-medium">Seller Name</span>
            <div className="flex items-center justify-between mt-0.5">
              <span className="font-semibold text-foreground truncate">{data.seller_name || "Data unavailable"}</span>
              {data.seller_profile_link && (
                <a href={data.seller_profile_link} target="_blank" rel="noreferrer" className="text-xs text-primary flex items-center gap-1 hover:underline">
                  Link <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-1 p-3 rounded-lg bg-muted/40 border border-border/40">
            <span className="text-xs text-muted-foreground font-medium">Seller Type & Verification</span>
            <div className="flex items-center gap-2 mt-0.5">
              <Badge variant="secondary" className="text-xs font-medium">
                {data.seller_type}
              </Badge>
              {data.business_verified ? (
                <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Verified
                </span>
              ) : (
                <span className="text-xs text-muted-foreground">Unverified</span>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-1 p-3 rounded-lg bg-muted/40 border border-border/40">
            <span className="text-xs text-muted-foreground font-medium">Seller Rating & Reviews</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              {data.seller_rating !== null ? (
                <>
                  <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                  <span className="font-semibold text-foreground">{data.seller_rating} / 5.0</span>
                  <span className="text-xs text-muted-foreground">({data.seller_review_count ?? "N/A"} reviews)</span>
                </>
              ) : (
                <span className="text-xs text-muted-foreground">Data unavailable</span>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-1 p-3 rounded-lg bg-muted/40 border border-border/40">
            <span className="text-xs text-muted-foreground font-medium">Return & Refund Policy</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <RotateCcw className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              <span className="text-xs font-medium text-foreground truncate">
                {data.return_policy || "Data unavailable"}
              </span>
            </div>
          </div>
        </div>

        {data.warranty && (
          <div className="flex items-center gap-2 p-2.5 rounded-md bg-primary/5 text-xs text-foreground border border-primary/10">
            <ShieldCheck className="h-4 w-4 text-primary shrink-0" />
            <span><strong>Warranty:</strong> {data.warranty}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
