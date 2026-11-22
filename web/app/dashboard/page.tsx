"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { createClient } from "@/lib/supabase";
import { fetchRepos, fetchReports } from "@/lib/api";
import { RepoCard } from "@/components/RepoCard";
import { AppShell, PageHeader } from "@/components/AppShell";
import { RepoCardSkeleton, StatSkeleton } from "@/components/DashboardSkeleton";
import type { ReportSummary } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        router.push("/login?next=/dashboard");
      } else {
        setToken(session.access_token);
      }
    });
  }, [router]);

  const { data: repos, error: reposError } = useSWR(
    token ? ["repos", token] : null,
    ([, t]) => fetchRepos(t)
  );

  const { data: reports, error: reportsError } = useSWR(
    token ? ["reports", token] : null,
    ([, t]) => fetchReports(t)
  );

  // Until the session and both lists have arrived, show placeholders
  // instead of counts of 0 and the empty state, which would be wrong.
  const loading =
    !token ||
    (repos === undefined && !reposError) ||
    (reports === undefined && !reportsError);

  // Group all reports by repo, sorted newest-first (API already returns desc)
  const reportsByRepo: Record<string, ReportSummary[]> = {};
  for (const r of reports ?? []) {
    const key = `${r.owner}/${r.repo}`;
    if (!reportsByRepo[key]) reportsByRepo[key] = [];
    reportsByRepo[key].push(r);
  }

  // Headline numbers, derived from the data already loaded above
  const latestScores = Object.values(reportsByRepo)
    .map((rs) => rs[0]?.score_composite)
    .filter((s): s is number => typeof s === "number");
  const stats = [
    { label: "Watched repos", value: repos?.length ?? 0 },
    { label: "High-intent leads", value: latestScores.filter((s) => s >= 70).length },
    { label: "Reports run", value: reports?.length ?? 0 },
  ];

  return (
    <AppShell>
      <div className="space-y-8">
        <PageHeader
          title="Dashboard"
          actions={
            <a
              href="/repos"
              className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Manage repos →
            </a>
          }
        />

        <dl aria-busy={loading} className="grid grid-cols-3 gap-2 sm:gap-3">
          {stats.map((s) => (
            <div key={s.label} className="rounded-lg border border-border bg-card p-3 sm:p-4">
              <dt className="text-xs text-muted-foreground">{s.label}</dt>
              {loading ? (
                <dd>
                  <StatSkeleton />
                </dd>
              ) : (
                <dd className="mt-1 font-mono text-xl font-medium sm:text-2xl tabular-nums text-foreground">{s.value}</dd>
              )}
            </div>
          ))}
        </dl>

        {loading ? (
          <div
            role="status"
            aria-label="Loading watched repos"
            className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3"
          >
            <RepoCardSkeleton />
            <RepoCardSkeleton />
          </div>
        ) : !repos || repos.length === 0 ? (
          <div className="rounded-lg border border-dashed border-input bg-card px-6 py-16 text-center text-muted-foreground">
            <p className="text-base font-medium text-foreground">No repos watched yet.</p>
            <a href="/repos" className="mt-2 inline-block text-sm text-link hover:underline">
              Add your first repo →
            </a>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {repos.map((r) => (
              <RepoCard
                key={`${r.owner}/${r.repo}`}
                owner={r.owner}
                repo={r.repo}
                label={r.label}
                lastChecked={r.last_checked}
                reports={reportsByRepo[`${r.owner}/${r.repo}`] ?? []}
              />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
