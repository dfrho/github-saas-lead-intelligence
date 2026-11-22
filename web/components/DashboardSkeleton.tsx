import { Skeleton } from "@/components/ui/skeleton";

/** Placeholder for one stat tile while dashboard data loads. */
export function StatSkeleton() {
  return <Skeleton className="mt-2 h-7 w-10 sm:h-8" />;
}

/** Placeholder shaped like a RepoCard plus its "Previous runs" list. */
export function RepoCardSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      <div className="rounded-lg border border-border bg-card p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1 space-y-2">
            <Skeleton className="h-5 w-2/5" />
            <Skeleton className="h-3.5 w-1/3" />
          </div>
          <Skeleton className="h-6 w-16" />
        </div>
        <Skeleton className="mt-4 h-6 w-24 rounded-full" />
        <div className="mt-3 flex items-center justify-between gap-3 border-t border-border pt-3">
          <Skeleton className="h-3.5 w-32" />
          <Skeleton className="h-3.5 w-20" />
        </div>
      </div>
      <div className="space-y-2 rounded-lg border border-border bg-card px-4 py-3">
        <Skeleton className="h-3.5 w-24" />
        {[0, 1, 2].map((i) => (
          <div key={i} className="flex items-center justify-between">
            <Skeleton className="h-3.5 w-20" />
            <Skeleton className="h-5 w-14" />
          </div>
        ))}
      </div>
    </div>
  );
}
