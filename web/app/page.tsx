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
    <main className="min-h-screen flex flex-col items-center bg-background px-4">
      <div className="max-w-lg w-full space-y-8 text-center pt-24 pb-16">
        <div>
          <h1 className="font-display font-bold text-4xl tracking-tight text-foreground">
            Repolytics
          </h1>
          <p className="mt-3 text-sm text-muted-foreground">
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
              className="w-full font-display font-semibold"
              disabled={loading}
            >
              {loading ? "Starting..." : "Analyze Repository →"}
            </Button>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </form>
        ) : (
          <div className="space-y-4 text-left bg-muted rounded-xl p-6">
            <p className="text-sm font-medium text-foreground">
              Analyzing <span className="font-mono">{owner}/{repo}</span>
            </p>
            <ProgressIndicator reportId={reportId} onComplete={handleComplete} />
            <p className="text-xs text-muted-foreground">
              Your report will be ready in about 30–60 seconds.
              You&apos;ll need to sign in to view it — we&apos;ll take you there automatically.
            </p>
          </div>
        )}

        <p className="text-sm text-muted-foreground">
          Already have an account?{" "}
          <a href="/login" className="text-primary hover:underline">Sign in</a>
        </p>
      </div>

      <HowItWorks />
    </main>
  );
}

const STEPS = [
  {
    title: "Read the repository",
    body: "We pull recent commits, pull requests and issues from a public GitHub repository, along with its dependency files.",
  },
  {
    title: "Work out what they're building",
    body: "Claude summarizes the activity and maps it to 20 SaaS categories such as auth, observability, messaging, payments and data infrastructure.",
  },
  {
    title: "Turn it into a lead",
    body: "We add the people doing the work, recent company news and the vendors that fit, then score the account and suggest how to open the conversation.",
  },
];

const REPORT_ITEMS = [
  {
    title: "Lead score",
    body: "A 0–100 score with a confidence label, built from five factors: activity, pain points, dependencies, team size and growth.",
  },
  {
    title: "Buying signals",
    body: "The infrastructure areas the team is investing in right now, with the commits and pull requests behind each one.",
  },
  {
    title: "Contacts",
    body: "The most active contributors, with their GitHub profiles, organizations and public employer details.",
  },
  {
    title: "Outreach angle",
    body: "A short, specific opening that ties what the team is building to a reason to talk now.",
  },
  {
    title: "Company news",
    body: "Recent blog posts, launches and press from the organization behind the repository.",
  },
  {
    title: "Vendor fit",
    body: "SaaS products in each signal category, so you can see where your offering lands and who you're up against.",
  },
];

function HowItWorks() {
  return (
    <div className="w-full max-w-4xl border-t border-border py-16 space-y-16">
      <section className="max-w-2xl mx-auto text-center space-y-3">
        <h2 className="font-display font-semibold text-2xl tracking-tight text-foreground">
          Code changes come before the RFP
        </h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          When an engineering team starts committing heavily to something new, such as a message
          queue, a login system or tracing, they usually go looking for a vendor in that area
          60 to 120 days later. Repolytics watches public repositories for those shifts and tells
          you which accounts are about to be in market, what they need, and who to talk to.
        </p>
      </section>

      <section className="space-y-6">
        <h2 className="font-display font-semibold text-xl tracking-tight text-foreground text-center">
          How it works
        </h2>
        <ol className="grid gap-4 sm:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step.title} className="rounded-xl border border-border bg-card p-5 space-y-2">
              <span className="font-mono text-xs text-muted-foreground">0{i + 1}</span>
              <h3 className="font-display font-semibold text-foreground">{step.title}</h3>
              <p className="text-sm leading-relaxed text-muted-foreground">{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="space-y-6">
        <h2 className="font-display font-semibold text-xl tracking-tight text-foreground text-center">
          What&apos;s in a report
        </h2>
        <div className="grid gap-x-8 gap-y-6 sm:grid-cols-2">
          {REPORT_ITEMS.map((item) => (
            <div key={item.title} className="space-y-1">
              <h3 className="font-display font-semibold text-foreground">{item.title}</h3>
              <p className="text-sm leading-relaxed text-muted-foreground">{item.body}</p>
            </div>
          ))}
        </div>
        <p className="text-sm text-muted-foreground text-center">
          Add a repository to your watch list and its report is re-run every week. Reports export to CSV or plain text.
        </p>
      </section>

      <section className="max-w-2xl mx-auto text-center space-y-3">
        <h2 className="font-display font-semibold text-xl tracking-tight text-foreground">
          Who it&apos;s for
        </h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          SaaS sales, BDR and go-to-market teams selling to engineering organizations. Repolytics
          only reads public repositories and public profile data, and it&apos;s free while we
          collect feedback.
        </p>
      </section>
    </div>
  );
}
