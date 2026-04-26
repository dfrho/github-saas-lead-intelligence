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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ProgressIndicator } from "@/components/ProgressIndicator";
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
      <main className="min-h-screen bg-white max-w-3xl mx-auto px-4 py-10">
        <div className="bg-white rounded-xl border border-gray-400 p-8 space-y-4">
          <h1 className="text-xl font-semibold text-gray-900">Generating your report...</h1>
          <ProgressIndicator reportId={id} onComplete={handleComplete} />
          <p className="text-sm text-gray-400">This usually takes 30–60 seconds.</p>
        </div>
      </main>
    );
  }

  if (!report) {
    return (
      <main className="max-w-3xl mx-auto px-4 py-10">
        <p className="text-gray-400 text-sm">Loading report...</p>
      </main>
    );
  }

  const json = report.json_body as Record<string, unknown> | null;
  const synopsis = json?.synopsis as string | undefined;
  const outreachAngle = json?.recommended_angle as string | undefined;
  const contributors = (json?.enrichment as Record<string, unknown>)?.top_contributors as Array<Record<string, unknown>> | undefined;
  const vendors = json?.vendors as Array<Record<string, unknown>> | undefined;

  return (
    <main className="min-h-screen bg-white max-w-3xl mx-auto px-4 py-10 space-y-8">
      <div className="flex items-center justify-between">
        <a href="/dashboard" className="text-sm text-blue-600 hover:underline">← Dashboard</a>
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
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle className="text-lg">{report.owner}/{report.repo}</CardTitle>
              <p className="text-xs text-gray-400 mt-1">
                Generated {new Date(report.run_at).toLocaleString()}
              </p>
            </div>
            <div className="text-right">
              <span className={`text-2xl font-bold px-3 py-1 rounded-lg ${scoreColor(report.score_composite)}`}>
                {report.score_composite}/100
              </span>
              {report.confidence_label && (
                <p className="text-sm text-gray-500 mt-1">{report.confidence_label}</p>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Score breakdown bars */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Score Breakdown</h3>
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
                <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Outreach Angle</h3>
                <button
                  onClick={() => { navigator.clipboard.writeText(outreachAngle); setCopied(true); setTimeout(() => setCopied(false), 5000); }}
                  title="Copy outreach angle"
                  className="text-gray-400 hover:text-gray-700 transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>
                    <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
                  </svg>
                </button>
                {copied && <span className="text-xs text-green-600 font-medium">Outreach copied</span>}
              </div>
              <p className="text-sm text-gray-700 leading-relaxed">{outreachAngle}</p>
            </div>
          )}

          {/* Top contributors */}
          {contributors && contributors.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-2">Top Contacts</h3>
              <div className="space-y-2">
                {contributors.slice(0, 3).map((c) => (
                  <div key={c.login as string} className="flex items-center justify-between text-sm">
                    <div>
                      <span className="font-medium">{c.name as string || c.login as string}</span>
                      {c.company ? <span className="text-gray-400 ml-2">· {String(c.company)}</span> : null}
                    </div>
                    <a
                      href={`https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(`${c.name || c.login} ${String(c.company || "").replace(/^@/, "")}`)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-500 hover:underline text-xs"
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
            <div>
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-2">Vendor Recommendations</h3>
              <div className="flex flex-wrap gap-2">
                {vendors.slice(0, 3).flatMap((v) =>
                  ((v.vendors as Array<Record<string, string>>) ?? []).slice(0, 2).map((vendor) => (
                    <Badge key={vendor.name} variant="outline">
                      {vendor.name}
                    </Badge>
                  ))
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Synopsis ─────────────────────────────────────────────────── */}
      {synopsis && (
        <div>
          <h2 className="text-base font-semibold text-gray-900 mb-2">Synopsis</h2>
          <p className="text-sm text-gray-700 leading-relaxed">{synopsis}</p>
        </div>
      )}

      {/* ── Full Markdown report ──────────────────────────────────────── */}
      {report.markdown_body && (
        <div>
          <h2 className="text-base font-semibold text-gray-900 mb-4">Full Report</h2>
          <div className="prose prose-sm prose-gray max-w-none border border-gray-400 rounded-xl p-6 bg-white text-gray-900">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
              {report.markdown_body}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </main>
  );
}
