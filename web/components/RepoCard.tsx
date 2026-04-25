"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { scoreColor } from "@/lib/utils";
import type { ReportSummary } from "@/lib/api";
import Link from "next/link";

interface RepoCardProps {
  owner: string;
  repo: string;
  label: string;
  lastChecked: string | null;
  latestReport: ReportSummary | null;
}

export function RepoCard({ owner, repo, label, lastChecked, latestReport }: RepoCardProps) {
  const score = latestReport?.score_composite ?? null;
  const confidence = latestReport?.confidence_label ?? null;

  return (
    <Card className="flex flex-col justify-between">
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
        {confidence && (
          <Badge variant="outline">{confidence}</Badge>
        )}
        <p className="text-xs text-gray-400">
          {lastChecked
            ? `Last checked ${new Date(lastChecked).toLocaleDateString()}`
            : "Never checked"}
        </p>
        {latestReport && (
          <Link href={`/reports/${latestReport.id}`}>
            <Button size="sm" variant="outline" className="w-full">
              View Report
            </Button>
          </Link>
        )}
      </CardContent>
    </Card>
  );
}
