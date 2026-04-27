"use client";

import { Badge } from "@/components/ui/badge";
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
    <Card className={`flex flex-col justify-between ${latest ? "hover:shadow-md transition-shadow cursor-pointer" : ""}`}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-base">{label}</CardTitle>
            <p className="text-xs text-gray-500 mt-0.5">{owner}/{repo}</p>
          </div>
          {score !== null && (
            <span className={`text-sm font-semibold px-2 py-0.5 rounded-full ${scoreColor(score)}`}>
              {score}/100
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {confidence && <Badge variant="outline">{confidence}</Badge>}
        <p className="text-xs text-gray-400">
          {lastChecked
            ? `Last checked ${new Date(lastChecked).toLocaleDateString()}`
            : "Never checked"}
        </p>
        {latest && (
          <span className="inline-flex items-center text-xs text-blue-600 font-medium">
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
        <div className="pl-2 border-l-2 border-gray-100 space-y-1">
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">Previous runs</p>
          {history.map((r) => (
            <Link
              key={r.id}
              href={`/reports/${r.id}`}
              className="flex items-center justify-between text-xs text-gray-600 hover:text-blue-600 py-0.5"
            >
              <span>{new Date(r.run_at).toLocaleDateString()}</span>
              {r.score_composite !== null && (
                <span className={`font-semibold px-1.5 py-0.5 rounded ${scoreColor(r.score_composite)}`}>
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
