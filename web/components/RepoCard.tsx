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
    <Card className={`flex flex-col justify-between rounded-2xl bg-muted border-none shadow-none ${latest ? "hover:shadow-md transition-shadow cursor-pointer" : ""}`}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-base">{label}</CardTitle>
            <p className="text-xs text-muted-foreground mt-0.5">{owner}/{repo}</p>
          </div>
          {score !== null && (
            <span className={`text-sm font-mono font-semibold px-2.5 py-0.5 rounded-full ${scoreColor(score)}`}>
              {score}/100
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {confidence && <span className="text-xs font-semibold text-muted-foreground">{confidence}</span>}
        <p className="text-xs text-muted-foreground">
          {lastChecked
            ? `Last checked ${new Date(lastChecked).toLocaleDateString()}`
            : "Never checked"}
        </p>
        {latest && (
          <span className="inline-flex items-center text-xs font-semibold text-primary">
            View Report →
          </span>
        )}
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-2">
      {latest ? (
        <Link href={`/reports/${latest.id}`} className="block">
          {cardInner}
        </Link>
      ) : cardInner}

      {/* Report history — older runs listed beneath the card */}
      {history.length > 0 && (
        <div className="pl-3 border-l-2 border-border space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Previous runs</p>
          {history.map((r) => (
            <Link
              key={r.id}
              href={`/reports/${r.id}`}
              className="flex items-center justify-between text-xs py-0.5 transition-colors text-foreground"
            >
              <span>{new Date(r.run_at).toLocaleDateString()}</span>
              {r.score_composite !== null && (
                <span className={`font-mono font-semibold px-1.5 py-0.5 rounded ${scoreColor(r.score_composite)}`}>
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
