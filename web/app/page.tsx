"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ProgressIndicator } from "@/components/ProgressIndicator";
import { triggerReport } from "@/lib/api";
import { createClient } from "@/lib/supabase";

export default function LandingPage() {
  const router = useRouter();
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [loading, setLoading] = useState(false);
  const [reportId, setReportId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleRun(e: React.FormEvent) {
    e.preventDefault();
    if (!owner.trim() || !repo.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await triggerReport(owner.trim(), repo.trim(), null);
      setReportId(data.report_id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start analysis");
      setLoading(false);
    }
  }

  const handleComplete = useCallback(async () => {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    if (session) {
      router.push(`/reports/${reportId}`);
    } else {
      router.push(`/login?next=/reports/${reportId}`);
    }
  }, [reportId, router]);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-white px-4">
      <div className="max-w-lg w-full space-y-8 text-center">
        <div>
          <h1
            className="text-4xl font-semibold tracking-tight"
            style={{ fontFamily: "var(--font-space-grotesk)", color: "#1a1a1a" }}
          >
            Repolytics
          </h1>
          <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
            Turns GitHub commit activity into purchase-intent signals for SaaS sales, BDR, and strategic GTM teams.
          </p>
        </div>

        {!reportId ? (
          <form onSubmit={handleRun} className="space-y-4 text-left">
            <div className="flex gap-3">
              <div className="flex-1 space-y-1">
                <Label htmlFor="owner">Owner</Label>
                <Input
                  id="owner"
                  placeholder="e.g. stripe"
                  value={owner}
                  onChange={(e) => setOwner(e.target.value)}
                />
              </div>
              <div className="flex-1 space-y-1">
                <Label htmlFor="repo">Repository</Label>
                <Input
                  id="repo"
                  placeholder="e.g. stripe-python"
                  value={repo}
                  onChange={(e) => setRepo(e.target.value)}
                />
              </div>
            </div>
            <Button
              type="submit"
              className="w-full text-white font-medium"
              style={{ backgroundColor: "#343ced" }}
              disabled={loading}
            >
              {loading ? "Starting..." : "Analyze Repository →"}
            </Button>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </form>
        ) : (
          <div className="space-y-4 text-left bg-white rounded-xl border border-gray-200 p-6">
            <p className="text-sm font-medium" style={{ color: "#484848" }}>
              Analyzing <span className="font-mono">{owner}/{repo}</span>
            </p>
            <ProgressIndicator reportId={reportId} onComplete={handleComplete} />
            <p className="text-xs" style={{ color: "#484848", opacity: 0.5 }}>
              Your report will be ready in about 30–60 seconds.
              You&apos;ll need to sign in to view it — we&apos;ll take you there automatically.
            </p>
          </div>
        )}

        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Already have an account?{" "}
          <a href="/login" className="hover:underline" style={{ color: "#343ced" }}>Sign in</a>
        </p>
      </div>
    </main>
  );
}
