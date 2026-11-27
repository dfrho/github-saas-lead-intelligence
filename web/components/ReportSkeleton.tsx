import { Skeleton } from "@/components/ui/skeleton";

/** Placeholder shaped like the report header, score card and breakdown. */
export function ReportSkeleton() {
  return (
    <div role="status" aria-label="Loading report" className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-3.5 w-20" />
        <Skeleton className="h-7 w-64 max-w-full" />
        <Skeleton className="h-3.5 w-40" />
      </div>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <div className="space-y-4 rounded-lg border border-border bg-card p-5">
          <Skeleton className="h-3.5 w-20" />
          <Skeleton className="h-10 w-32" />
          <Skeleton className="h-4 w-40" />
        </div>
        <div className="space-y-4 rounded-lg border border-border bg-card p-5">
          <Skeleton className="h-3.5 w-28" />
          <div className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
            {[0, 1, 2, 3, 4].map((i) => (
              <div key={i} className="space-y-1.5">
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-2 w-full rounded-full" />
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="space-y-2 rounded-lg border border-border bg-card p-5">
        <Skeleton className="h-3.5 w-28" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    </div>
  );
}
