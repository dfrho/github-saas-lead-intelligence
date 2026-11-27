"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ProgressIndicator } from "@/components/ProgressIndicator";
import { triggerReport } from "@/lib/api";
import { createClient } from "@/lib/supabase";
import { LogoMark } from "@/components/Logo";

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
    <main className="flex min-h-screen flex-col items-center bg-background px-4 sm:px-6">
      <div className="w-full max-w-xl space-y-8 pb-16 pt-16 text-center sm:pt-28">
        <div>
          <div className="mb-8 flex items-center justify-center gap-2.5">
            <LogoMark className="h-8 w-8 text-foreground" />
            <span className="font-display text-xl font-bold tracking-tight text-foreground">Repolytics</span>
          </div>
          <h1 className="font-display text-4xl font-bold tracking-tight text-balance text-foreground sm:text-6xl">
            Code changes come before the RFP
          </h1>
          <p className="mx-auto mt-4 max-w-md text-base leading-relaxed text-muted-foreground sm:text-lg">
            Repolytics turns GitHub commit activity into purchase-intent signals for SaaS GTM teams.
          </p>
          <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-muted-foreground">
            Enter any public repository to see what the team is building and who to talk to.
          </p>
        </div>

        {!reportId ? (
          <form onSubmit={handleRun} className="space-y-4 rounded-xl border border-border bg-card p-5 text-left shadow-sm sm:p-6">
            <div className="flex flex-col gap-3 sm:flex-row">
              <div className="flex-1 space-y-1.5">
                <Label htmlFor="owner">Owner</Label>
                <Input
                  id="owner"
                  placeholder="e.g. stripe"
                  value={owner}
                  onChange={(e) => setOwner(e.target.value)}
                />
              </div>
              <div className="flex-1 space-y-1.5">
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
              size="lg"
              className="w-full"
              disabled={loading}
            >
              {loading ? "Starting..." : "Get the lead report →"}
            </Button>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </form>
        ) : (
          <div className="space-y-4 rounded-xl border border-border bg-card p-5 text-left shadow-sm sm:p-6">
            <p className="text-sm font-medium text-foreground">
              Analyzing <span className="break-all font-mono">{owner}/{repo}</span>
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
          <a href="/login" className="font-medium text-link hover:underline">Sign in</a>
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
    <div className="w-full max-w-5xl space-y-16 border-t border-border py-16 sm:space-y-20 sm:py-20">
      <section className="max-w-2xl mx-auto text-center space-y-3">
        <h2 className="font-display text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Why Repolytics exists
        </h2>
        <p className="text-left text-base leading-relaxed text-muted-foreground sm:text-center">
          When an engineering team starts committing heavily to something new, such as a message
          queue, a login system or tracing, it tends to go looking for a vendor in that area
          60 to 120 days later. That&apos;s the premise we&apos;re testing during the free period.
          Repolytics watches public repositories for those shifts and tells you which accounts are
          about to be in market, what they need, and who to talk to.
        </p>
      </section>

      <section className="max-w-2xl mx-auto text-center space-y-3">
        <h2 className="font-display text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
          Who it&apos;s for
        </h2>
        <p className="text-left text-base leading-relaxed text-muted-foreground sm:text-center">
          SaaS GTM teams selling to engineering organizations. If you sell in a category like auth,
          observability, messaging, payments or data infrastructure, Repolytics shows you which
          teams have started work in your area.
        </p>
      </section>

      <section className="space-y-6">
        <h2 className="font-display text-xl font-semibold tracking-tight text-foreground sm:text-2xl text-center">
          How it works
        </h2>
        <ol className="grid gap-4 sm:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step.title} className="space-y-2 rounded-lg border border-border bg-card p-5">
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-foreground font-mono text-xs text-background">0{i + 1}</span>
              <h3 className="font-display font-semibold text-foreground">{step.title}</h3>
              <p className="text-sm leading-relaxed text-muted-foreground">{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="space-y-6">
        <h2 className="font-display text-xl font-semibold tracking-tight text-foreground sm:text-2xl text-center">
          What&apos;s in a report
        </h2>
        <div className="grid gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-2 lg:grid-cols-3">
          {REPORT_ITEMS.map((item) => (
            <div key={item.title} className="space-y-1 bg-card p-5">
              <h3 className="font-display font-semibold text-foreground">{item.title}</h3>
              <p className="text-sm leading-relaxed text-muted-foreground">{item.body}</p>
            </div>
          ))}
        </div>
        <p className="text-sm text-muted-foreground text-center">
          Add a repository to your watch list and its report is re-run every week. Reports export to CSV or plain text.
        </p>
      </section>

      <p className="text-sm text-muted-foreground text-center">
        Repolytics only reads public repositories and public profile data, and it&apos;s free
        while we collect feedback.
      </p>
    </div>
  );
}
