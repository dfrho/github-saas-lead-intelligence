"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { createClient } from "@/lib/supabase";
import { fetchReport, fetchReportStatus, exportReportUrl } from "@/lib/api";
import { ScoreBar } from "@/components/ScoreBar";
import { Button } from "@/components/ui/button";
import { ProgressIndicator } from "@/components/ProgressIndicator";
import { NavBar } from "@/components/NavBar";
import { scoreColor } from "@/lib/utils";

export default function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);

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

  function handleComplete() {
    setIsGenerating(false);
    mutate();
  }

  if (!token) return null;

  if (isGenerating) {
    return (
      <main className="min-h-screen bg-background max-w-3xl mx-auto px-4 py-10">
        <div className="bg-muted rounded-2xl p-8 space-y-4">
          <h1 className="font-display font-bold text-xl text-foreground">Generating your report...</h1>
          <ProgressIndicator reportId={id} onComplete={handleComplete} />
          <p className="text-sm text-muted-foreground">This usually takes 30–60 seconds.</p>
        </div>
      </main>
    );
  }

  if (!report) {
    return (
      <main className="max-w-3xl mx-auto px-4 py-10">
        <p className="text-muted-foreground text-sm">Loading report...</p>
      </main>
    );
  }

  const json = report.json_body as Record<string, unknown> | null;
  const synopsis = json?.synopsis as string | undefined;
  const outreachAngle = json?.recommended_angle as string | undefined;
  const contributors = (json?.enrichment as Record<string, unknown>)?.top_contributors as Array<Record<string, unknown>> | undefined;
  const vendors = json?.vendors as Array<Record<string, unknown>> | undefined;

  return (
    <>
    <NavBar />
    <main className="min-h-screen bg-background max-w-3xl mx-auto px-4 py-10 space-y-8">
      <div className="flex items-center justify-end">
        <div className="flex gap-2">
          <a href={exportReportUrl(id, "csv")} download>
            <Button size="sm" variant="outline">Export CSV</Button>
          </a>
          <a href={exportReportUrl(id, "txt")} download>
            <Button size="sm" variant="outline">Export TXT</Button>
          </a>
        </div>
      </div>

      {/* ── Summary card ─────────────────────────────────────────────── */}
      <div className="bg-muted rounded-2xl p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="font-display font-bold text-lg text-foreground">{report.owner}/{report.repo}</p>
            <p className="text-xs mt-1 text-muted-foreground">
              Generated {new Date(report.run_at).toLocaleString()}
            </p>
          </div>
          <div className="text-right">
            <span className={`font-display text-2xl font-bold px-3 py-1 rounded-lg ${scoreColor(report.score_composite)}`}>
              {report.score_composite}/100
            </span>
            {report.confidence_label && (
              <p className="text-sm mt-1 text-muted-foreground">{report.confidence_label}</p>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-8">
        {/* Score breakdown bars */}
        <div className="space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Score Breakdown</h3>
          <ScoreBar label="Activity" score={report.score_activity} weight="25%" />
          <ScoreBar label="Pain Points" score={report.score_pain_points} weight="25%" />
          <ScoreBar label="Dependencies" score={report.score_dependencies} weight="20%" />
          <ScoreBar label="Team Size" score={report.score_team_size} weight="15%" />
          <ScoreBar label="Growth Signals" score={report.score_growth} weight="15%" />
        </div>

        {/* Outreach angle */}
        {outreachAngle && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Outreach Angle</h3>
              <button
                onClick={() => { navigator.clipboard.writeText(outreachAngle); setCopied(true); setTimeout(() => setCopied(false), 5000); }}
                title="Copy outreach angle"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>
                  <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
                </svg>
              </button>
              {copied && <span className="text-xs text-good font-medium">Outreach copied</span>}
            </div>
            <p className="text-sm leading-relaxed text-foreground">{outreachAngle}</p>
          </div>
        )}

        {/* Top contributors */}
        {contributors && contributors.length > 0 && (
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-widest mb-2 text-muted-foreground">Top Contacts</h3>
            <div className="space-y-2">
              {contributors.slice(0, 3).map((c) => (
                <div key={c.login as string} className="flex items-center justify-between text-sm">
                  <div>
                    <span className="font-medium text-foreground">{c.name as string || c.login as string}</span>
                    {c.company ? <span className="text-muted-foreground ml-2">· {String(c.company)}</span> : null}
                  </div>
                  <a
                    href={`https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(`${c.name || c.login} ${String(c.company || "").replace(/^@/, "")}`)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-semibold text-primary hover:underline"
                  >
                    Find on LinkedIn →
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Vendor recommendations */}
        {vendors && vendors.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Vendor Recommendations</h3>
            {vendors.slice(0, 3).map((v) => (
              <div key={v.domain as string}>
                <p className="text-xs font-semibold mb-1.5 text-primary">
                  {(v.domain as string).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                </p>
                <div className="flex flex-wrap gap-2">
                  {((v.vendors as Array<Record<string, string>>) ?? []).slice(0, 2).map((vendor) => (
                    <span key={vendor.name} className="text-xs font-medium bg-muted rounded-full px-3 py-1 text-foreground">{vendor.name}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Synopsis ─────────────────────────────────────────────────── */}
      {synopsis && (
        <div>
          <h2 className="font-display font-bold text-base mb-2 text-foreground">Synopsis</h2>
          <div className="prose prose-sm max-w-none text-sm leading-relaxed text-foreground">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{synopsis}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* ── Full Markdown report ──────────────────────────────────────── */}
      {report.markdown_body && (
        <div>
          <h2 className="font-display font-bold text-base mb-4 text-foreground">Full Report</h2>
          <div className="prose prose-sm max-w-none bg-muted rounded-2xl p-6 text-foreground">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
              {report.markdown_body}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </main>
    </>
  );
}
