"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { fetchProfile, upsertProfile } from "@/lib/api";
import { NavBar } from "@/components/NavBar";
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
    <>
      <NavBar />
      <main className="min-h-screen bg-white max-w-lg mx-auto px-4 py-10 space-y-8">
        <h1 className="text-2xl font-bold text-gray-900">Account</h1>

        <div className="border border-gray-200 rounded-xl p-6 space-y-6">
          {/* Email — read-only */}
          <div className="space-y-1">
            <Label className="text-gray-700">Email</Label>
            <p className="text-sm text-gray-500">{email}</p>
          </div>

          {/* Editable profile fields */}
          <form onSubmit={handleSave} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="company">Company name</Label>
              <Input
                id="company"
                placeholder="e.g. Acme Corp"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="domain">Work domain</Label>
              <Input
                id="domain"
                placeholder="e.g. acme.com"
                value={workDomain}
                onChange={(e) => setWorkDomain(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-3">
              <Button
                type="submit"
                disabled={saving}
                className="bg-gray-700 hover:bg-gray-800 text-white"
              >
                {saving ? "Saving..." : "Save changes"}
              </Button>
              {saved && <span className="text-sm text-green-600">Saved</span>}
              {error && <span className="text-sm text-red-600">{error}</span>}
            </div>
          </form>
        </div>

        <div className="border border-gray-200 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Sign out</h2>
          <Button
            variant="outline"
            className="border-gray-300 text-gray-700 hover:bg-gray-50"
            onClick={handleSignOut}
          >
            Sign out
          </Button>
        </div>
      </main>
    </>
  );
}
