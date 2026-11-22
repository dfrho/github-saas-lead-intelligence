"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { watchRepo } from "@/lib/api";

interface AddRepoFormProps {
  token: string;
  onAdded: () => void;
}

export function AddRepoForm({ token, onAdded }: AddRepoFormProps) {
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [label, setLabel] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!owner.trim() || !repo.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await watchRepo(token, owner.trim(), repo.trim(), label.trim() || undefined);
      setOwner("");
      setRepo("");
      setLabel("");
      onAdded();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add repo");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid grid-cols-1 items-end gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_auto]">
      <div className="space-y-1.5">
        <Label htmlFor="owner">Owner</Label>
        <Input
          id="owner"
          placeholder="e.g. stripe"
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="repo">Repo</Label>
        <Input
          id="repo"
          placeholder="e.g. stripe-python"
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="label">Label (optional)</Label>
        <Input
          id="label"
          placeholder="e.g. Stripe SDK"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
        />
      </div>
      <Button
        type="submit"
        disabled={loading}
        className="w-full lg:w-auto"
      >
        {loading ? "Adding..." : "Watch Repo"}
      </Button>
      {error && <p className="text-sm text-destructive sm:col-span-2 lg:col-span-4">{error}</p>}
    </form>
  );
}
