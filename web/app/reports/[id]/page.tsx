"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { createClient } from "@/lib/supabase";
import { fetchReport, fetchReportStatus, downloadReport } from "@/lib/api";
import { ScoreBar } from "@/components/ScoreBar";
import { Button } from "@/components/ui/button";
import { ProgressIndicator } from "@/components/ProgressIndicator";
import { AppShell } from "@/components/AppShell";
import { scoreColor } from "@/lib/utils";

export default function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (!session) {
        router.push(`/login?next=/reports/${id}`);
        return;
      }
      setToken(session.access_token);

      // Check if report is still in progress
      try {
        const status = await fetchReportStatus(id);
        if (status.status !== "complete" && !status.status.startsWith("error")) {
          setIsGenerating(true);
        }
      } catch {
        // report may not exist — SWR will handle the error state
      }
    });
  }, [id, router]);

  const { data: report, mutate } = useSWR(
    token && !isGenerating ? ["report", token, id] : null,
    ([, t, rid]) => fetchReport(t, rid)
  );

  async function handleExport(format: "csv" | "txt") {
    if (!token) return;
    setExportError(null);
    try {
      await downloadReport(token, id, format);
    } catch (err: unknown) {
      setExportError(err instanceof Error ? err.message : "Export failed");
    }
  }

  function handleComplete() {
    setIsGenerating(false);
    mutate();
  }

  if (!token) return null;

  if (isGenerating) {
    return (
      <AppShell width="default">
        <div className="space-y-4 rounded-lg border border-border bg-card p-6 sm:p-8">
          <h1 className="font-display text-xl font-semibold text-foreground">Generating your report...</h1>
          <ProgressIndicator reportId={id} onComplete={handleComplete} />
          <p className="text-sm text-muted-foreground">This usually takes 30–60 seconds.</p>
        </div>
      </AppShell>
    );
  }

  if (!report) {
    return (
      <AppShell width="default">
        <p className="text-sm text-muted-foreground" role="status">Loading report...</p>
      </AppShell>
    );
  }

  if (report.status !== "complete") {
    const failed = report.status.startsWith("error");
    const reason = failed ? report.status.replace(/^error:\s*/, "") : report.status;
    return (
      <AppShell width="default">
        <div className="space-y-4 rounded-lg border border-border bg-card p-6 sm:p-8">
          <p className="break-all font-mono text-sm text-muted-foreground">{report.owner}/{report.repo}</p>
          <h1 className="font-display text-xl font-semibold text-foreground">
            {failed ? "This report couldn't be generated" : "This report isn't finished"}
          </h1>
          <p className="text-sm text-muted-foreground">{reason}</p>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="sm">
              <Link href="/">Run a new report</Link>
            </Button>
            <Button asChild size="sm" variant="outline">
              <Link href="/dashboard">Back to dashboard</Link>
            </Button>
          </div>
        </div>
      </AppShell>
    );
  }

  const json = report.json_body as Record<string, unknown> | null;
  const synopsis = json?.synopsis as string | undefined;
  const outreachAngle = json?.recommended_angle as string | undefined;
  const contributors = (json?.enrichment as Record<string, unknown>)?.top_contributors as Array<Record<string, unknown>> | undefined;
  const vendors = json?.vendors as Array<Record<string, unknown>> | undefined;

  const sectionTitle = "text-xs font-medium uppercase tracking-wider text-muted-foreground";

  return (
    <AppShell>
      <div className="space-y-6">
        {/* ── Header ───────────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <p className="text-xs text-muted-foreground">Lead report</p>
            <h1 className="break-all font-mono text-xl font-medium text-foreground sm:text-2xl">
              {report.owner}/{report.repo}
            </h1>
            <p className="text-xs text-muted-foreground">
              Generated {new Date(report.run_at).toLocaleString()}
            </p>
          </div>
          <div className="flex flex-col items-stretch gap-2 sm:items-end">
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => handleExport("csv")}>
                Export CSV
              </Button>
              <Button size="sm" variant="outline" onClick={() => handleExport("txt")}>
                Export TXT
              </Button>
            </div>
            {exportError && <p className="text-sm text-destructive">{exportError}</p>}
          </div>
        </div>

        {/* ── Summary card ─────────────────────────────────────────────── */}
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
          <div className="flex flex-col justify-between gap-4 rounded-lg border border-border bg-card p-5">
            <h2 className={sectionTitle}>Lead score</h2>
            <div className="flex items-end gap-3">
              <span className={`rounded-md px-3 py-1 font-mono text-3xl font-medium tabular-nums ${scoreColor(report.score_composite)}`}>
                {report.score_composite}/100
              </span>
            </div>
            {report.confidence_label && (
              <p className="text-sm text-muted-foreground">{report.confidence_label}</p>
            )}
          </div>

          <div className="space-y-4 rounded-lg border border-border bg-card p-5">
            <h2 className={sectionTitle}>Score Breakdown</h2>
            <div className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
              <ScoreBar label="Activity" score={report.score_activity} weight="25%" />
              <ScoreBar label="Pain Points" score={report.score_pain_points} weight="25%" />
              <ScoreBar label="Dependencies" score={report.score_dependencies} weight="20%" />
              <ScoreBar label="Team Size" score={report.score_team_size} weight="15%" />
              <ScoreBar label="Growth Signals" score={report.score_growth} weight="15%" />
            </div>
          </div>
        </div>

        {/* Outreach angle */}
        {outreachAngle && (
          <section className="rounded-lg border border-border bg-card p-5">
            <div className="mb-3 flex items-center gap-2">
              <h2 className={sectionTitle}>Outreach Angle</h2>
              <button
                onClick={() => { navigator.clipboard.writeText(outreachAngle); setCopied(true); setTimeout(() => setCopied(false), 5000); }}
                title="Copy outreach angle"
                aria-label="Copy outreach angle"
                className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>
                  <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
                </svg>
              </button>
              {copied && <span className="text-xs font-medium text-good" role="status">Outreach copied</span>}
            </div>
            <p className="text-[15px] leading-relaxed text-foreground">{outreachAngle}</p>
          </section>
        )}

        <div className="grid gap-4 lg:grid-cols-2">
          {/* Top contributors */}
          {contributors && contributors.length > 0 && (
            <section className="rounded-lg border border-border bg-card p-5">
              <h2 className={`${sectionTitle} mb-3`}>Top Contacts</h2>
              <ul className="divide-y divide-border">
                {contributors.slice(0, 3).map((c) => (
                  <li key={c.login as string} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm first:pt-0 last:pb-0">
                    <div className="min-w-0">
                      <span className="font-medium text-foreground">{c.name as string || c.login as string}</span>
                      {c.company ? <span className="ml-2 text-muted-foreground">· {String(c.company)}</span> : null}
                    </div>
                    <a
                      href={`https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(`${c.name || c.login} ${String(c.company || "").replace(/^@/, "")}`)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs font-medium text-link hover:underline"
                    >
                      Find on LinkedIn →
                    </a>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Vendor recommendations */}
          {vendors && vendors.length > 0 && (
            <section className="space-y-4 rounded-lg border border-border bg-card p-5">
              <h2 className={sectionTitle}>Vendor Recommendations</h2>
              {vendors.slice(0, 3).map((v) => (
                <div key={v.domain as string}>
                  <p className="mb-1.5 text-sm font-medium text-foreground">
                    {(v.domain as string).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {((v.vendors as Array<Record<string, string>>) ?? []).slice(0, 2).map((vendor) => (
                      <span key={vendor.name} className="rounded-full border border-border px-3 py-1 text-xs font-medium text-foreground">{vendor.name}</span>
                    ))}
                  </div>
                </div>
              ))}
            </section>
          )}
        </div>

        {/* ── Synopsis ─────────────────────────────────────────────────── */}
        {synopsis && (
          <section className="rounded-lg border border-border bg-card p-5 sm:p-6">
            <h2 className="mb-3 font-display text-base font-semibold text-foreground">Synopsis</h2>
            <div className="prose max-w-none text-sm text-foreground">
              <ReactMarkdown remarkPlugins={[remarkGfm]} disallowedElements={["img"]}>
                {synopsis}
              </ReactMarkdown>
            </div>
          </section>
        )}

        {/* ── Full Markdown report ──────────────────────────────────────── */}
        {report.markdown_body && (
          <section className="rounded-lg border border-border bg-card p-5 sm:p-8">
            <h2 className="mb-4 font-display text-base font-semibold text-foreground">Full Report</h2>
            <div className="prose max-w-none text-sm text-foreground">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                disallowedElements={["img"]}
              >
                {report.markdown_body}
              </ReactMarkdown>
            </div>
          </section>
        )}
      </div>
    </AppShell>
  );
}
