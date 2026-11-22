"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { fetchProfile, upsertProfile } from "@/lib/api";
import { AppShell, PageHeader } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function AccountPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [companyName, setCompanyName] = useState("");
  const [workDomain, setWorkDomain] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (!session) {
        router.push("/login?next=/account");
        return;
      }
      setToken(session.access_token);
      setEmail(session.user.email ?? null);

      try {
        const profile = await fetchProfile(session.access_token);
        setCompanyName(profile.company_name ?? "");
        setWorkDomain(profile.work_domain ?? "");
      } catch {
        // profile may not exist yet — start empty
      }
    });
  }, [router]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    setError(null);
    try {
      await upsertProfile(token, companyName, workDomain);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
  }

  if (!token) return null;

  return (
    <AppShell width="narrow">
      <div className="space-y-8">
        <PageHeader title="Account" />

        <section className="rounded-lg border border-border bg-card">
          <div className="border-b border-border p-5">
            <h2 className="text-sm font-semibold text-foreground">Profile</h2>
          </div>
          <div className="space-y-6 p-5">
            {/* Email: read-only */}
            <div className="space-y-1.5">
              <Label className="text-foreground">Email</Label>
              <p className="break-all text-sm text-muted-foreground">{email}</p>
            </div>

            {/* Editable profile fields */}
            <form onSubmit={handleSave} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="company">Company name</Label>
                <Input
                  id="company"
                  placeholder="e.g. Acme Corp"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="domain">Work domain</Label>
                <Input
                  id="domain"
                  placeholder="e.g. acme.com"
                  value={workDomain}
                  onChange={(e) => setWorkDomain(e.target.value)}
                />
              </div>
              <div className="flex flex-wrap items-center gap-3 pt-1">
                <Button type="submit" disabled={saving}>
                  {saving ? "Saving..." : "Save changes"}
                </Button>
                {saved && <span className="text-sm text-good">Saved</span>}
                {error && <span className="text-sm text-destructive">{error}</span>}
              </div>
            </form>
          </div>
        </section>

        <section className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-border bg-card p-5">
          <h2 className="text-sm font-semibold text-foreground">Sign out</h2>
          <Button variant="outline" onClick={handleSignOut}>
            Sign out
          </Button>
        </section>
      </div>
    </AppShell>
  );
}
