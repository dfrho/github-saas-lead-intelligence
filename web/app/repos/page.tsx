"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { createClient } from "@/lib/supabase";
import { fetchRepos, removeRepo, triggerReport } from "@/lib/api";
import { AddRepoForm } from "@/components/AddRepoForm";
import { Button } from "@/components/ui/button";
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
    <main className="max-w-4xl mx-auto px-4 py-10 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Watched Repos</h1>
        <a href="/dashboard" className="text-sm text-blue-600 hover:underline">
          ← Dashboard
        </a>
      </div>

      <AddRepoForm token={token} onAdded={() => mutate()} />

      {repos && repos.length > 0 && (
        <Table>
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
                <TableCell className="text-sm text-gray-600">{r.label}</TableCell>
                <TableCell className="text-sm text-gray-400">
                  {r.last_checked
                    ? new Date(r.last_checked).toLocaleDateString()
                    : "Never"}
                </TableCell>
                <TableCell className="text-right space-x-2">
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
                    className="text-red-500 hover:text-red-700"
                    onClick={() => handleRemove(r.owner, r.repo)}
                  >
                    Remove
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {repos && repos.length === 0 && (
        <p className="text-sm text-gray-400">No repos watched yet. Add one above.</p>
      )}
    </main>
  );
}
