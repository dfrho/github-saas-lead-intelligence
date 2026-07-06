"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { createClient } from "@/lib/supabase";
import { fetchRepos, fetchReports } from "@/lib/api";
import { RepoCard } from "@/components/RepoCard";
import { NavBar } from "@/components/NavBar";
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

  const { data: repos } = useSWR(
    token ? ["repos", token] : null,
    ([, t]) => fetchRepos(t)
  );

  const { data: reports } = useSWR(
    token ? ["reports", token] : null,
    ([, t]) => fetchReports(t)
  );

  if (!token) return null;

  // Group all reports by repo, sorted newest-first (API already returns desc)
  const reportsByRepo: Record<string, ReportSummary[]> = {};
  for (const r of reports ?? []) {
    const key = `${r.owner}/${r.repo}`;
    if (!reportsByRepo[key]) reportsByRepo[key] = [];
    reportsByRepo[key].push(r);
  }

  return (
    <>
    <NavBar />
    <main className="max-w-5xl mx-auto px-4 py-10 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="font-display font-bold text-2xl text-foreground">Dashboard</h1>
        <a href="/repos" className="text-sm text-primary hover:underline">
          Manage repos →
        </a>
      </div>

      {!repos || repos.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <p className="text-lg">No repos watched yet.</p>
          <a href="/repos" className="text-sm mt-2 inline-block text-primary hover:underline">
            Add your first repo →
          </a>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
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
    </main>
    </>
  );
}
