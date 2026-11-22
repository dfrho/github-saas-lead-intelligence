"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { createClient } from "@/lib/supabase";
import { fetchRepos, removeRepo, triggerReport } from "@/lib/api";
import { AddRepoForm } from "@/components/AddRepoForm";
import { Button } from "@/components/ui/button";
import { AppShell, PageHeader } from "@/components/AppShell";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function ReposPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [runningRepo, setRunningRepo] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) router.push("/login?next=/repos");
      else setToken(session.access_token);
    });
  }, [router]);

  const { data: repos, mutate } = useSWR(
    token ? ["repos", token] : null,
    ([, t]) => fetchRepos(t)
  );

  async function handleRemove(owner: string, repo: string) {
    if (!token) return;
    await removeRepo(token, owner, repo);
    mutate();
  }

  async function handleRunReport(owner: string, repo: string) {
    if (!token) return;
    setRunningRepo(`${owner}/${repo}`);
    try {
      const data = await triggerReport(owner, repo, token);
      router.push(`/reports/${data.report_id}`);
    } finally {
      setRunningRepo(null);
    }
  }

  if (!token) return null;

  return (
    <AppShell width="default">
      <div className="space-y-8">
        <PageHeader
          title="Watched Repos"
          actions={
            <a href="/dashboard" className="text-sm text-link hover:underline">
              ← Dashboard
            </a>
          }
        />

        <section className="rounded-lg border border-border bg-card p-5">
          <h2 className="mb-4 text-sm font-semibold text-foreground">Add a repository</h2>
          <AddRepoForm token={token} onAdded={() => mutate()} />
        </section>

        {repos && repos.length > 0 && (
          <div className="overflow-hidden rounded-lg border border-border bg-card">
            <Table className="min-w-[640px]">
              <TableHeader>
                <TableRow>
                  <TableHead>Repo</TableHead>
                  <TableHead>Label</TableHead>
                  <TableHead>Last checked</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {repos.map((r) => (
                  <TableRow key={`${r.owner}/${r.repo}`}>
                    <TableCell className="font-mono text-sm">{r.owner}/{r.repo}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{r.label}</TableCell>
                    <TableCell className="whitespace-nowrap text-sm text-muted-foreground">
                      {r.last_checked
                        ? new Date(r.last_checked).toLocaleDateString()
                        : "Never"}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-right">
                      <div className="inline-flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={runningRepo === `${r.owner}/${r.repo}`}
                          onClick={() => handleRunReport(r.owner, r.repo)}
                        >
                          {runningRepo === `${r.owner}/${r.repo}` ? "Running..." : "Run report"}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-destructive hover:text-destructive"
                          onClick={() => handleRemove(r.owner, r.repo)}
                        >
                          Remove
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {repos && repos.length === 0 && (
          <p className="rounded-lg border border-dashed border-input bg-card px-6 py-10 text-center text-sm text-muted-foreground">
            No repos watched yet. Add one above.
          </p>
        )}
      </div>
    </AppShell>
  );
}
