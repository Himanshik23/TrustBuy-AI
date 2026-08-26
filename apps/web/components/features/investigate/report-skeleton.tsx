import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

/** Shown instead of a bare spinner while an investigation's first byte of
 * data is still loading - shaped like the real report (header, verdict,
 * evidence) so the layout doesn't jump once actual content arrives. */
export function ReportSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-busy="true" aria-label="Loading investigation report">
      <Card>
        <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-6 w-2/3" />
            <Skeleton className="h-4 w-1/3" />
          </div>
          <Skeleton className="h-6 w-24" />
        </CardHeader>
      </Card>

      <Card>
        <CardContent className="flex flex-col gap-4 py-6">
          <div className="flex items-center justify-between gap-4">
            <Skeleton className="h-9 w-40 rounded-full" />
            <Skeleton className="h-8 w-28" />
          </div>
          <div className="flex items-center gap-5">
            <Skeleton className="h-[156px] w-[156px] shrink-0 rounded-full" />
            <div className="flex flex-1 flex-col gap-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
