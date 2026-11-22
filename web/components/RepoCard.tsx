"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { scoreColor } from "@/lib/utils";
import type { ReportSummary } from "@/lib/api";
import Link from "next/link";

interface RepoCardProps {
  owner: string;
  repo: string;
  label: string;
  lastChecked: string | null;
  reports: ReportSummary[];
}

export function RepoCard({ owner, repo, label, lastChecked, reports }: RepoCardProps) {
  const latest = reports[0] ?? null;
  const history = reports.slice(1);
  const score = latest?.score_composite ?? null;
  const confidence = latest?.confidence_label ?? null;

  const cardInner = (
    <Card
      className={`flex h-full flex-col justify-between ${
        latest ? "transition-colors hover:border-foreground/30" : ""
      }`}
    >
      <CardHeader className="space-y-0 p-5 pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="truncate text-base">{label}</CardTitle>
            <p className="mt-1 truncate font-mono text-xs text-muted-foreground">{owner}/{repo}</p>
          </div>
          {score !== null && (
            <span className={`shrink-0 rounded-md px-2 py-0.5 font-mono text-sm font-medium tabular-nums ${scoreColor(score)}`}>
              {score}/100
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3 p-5 pt-0">
        {confidence && (
          <span className="inline-flex rounded-full border border-border px-2.5 py-0.5 text-xs font-medium text-foreground">
            {confidence}
          </span>
        )}
        <div className="flex items-center justify-between gap-3 border-t border-border pt-3">
          <p className="text-xs text-muted-foreground">
            {lastChecked
              ? `Last checked ${new Date(lastChecked).toLocaleDateString()}`
              : "Never checked"}
          </p>
          {latest && (
            <span className="inline-flex items-center text-xs font-medium text-link">
              View Report →
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="flex flex-col gap-2">
      {latest ? (
        <Link
          href={`/reports/${latest.id}`}
          className="block h-full rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {cardInner}
        </Link>
      ) : cardInner}

      {/* Report history: older runs listed beneath the card */}
      {history.length > 0 && (
        <div className="rounded-lg border border-border bg-card px-3 py-2">
          <p className="pb-1 text-xs font-medium text-muted-foreground">Previous runs</p>
          {history.map((r) => (
            <Link
              key={r.id}
              href={`/reports/${r.id}`}
              className="flex min-h-9 items-center justify-between rounded px-1 text-xs text-foreground transition-colors hover:bg-accent"
            >
              <span>{new Date(r.run_at).toLocaleDateString()}</span>
              {r.score_composite !== null && (
                <span className={`rounded px-1.5 py-0.5 font-mono font-medium tabular-nums ${scoreColor(r.score_composite)}`}>
                  {r.score_composite}/100
                </span>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
