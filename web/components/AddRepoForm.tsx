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
    <form onSubmit={handleSubmit} className="flex flex-wrap gap-3 items-end">
      <div className="space-y-1">
        <Label htmlFor="owner">Owner</Label>
        <Input
          id="owner"
          placeholder="e.g. stripe"
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
          className="w-36"
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="repo">Repo</Label>
        <Input
          id="repo"
          placeholder="e.g. stripe-python"
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          className="w-48"
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="label">Label (optional)</Label>
        <Input
          id="label"
          placeholder="e.g. Stripe SDK"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          className="w-40"
        />
      </div>
      <Button type="submit" disabled={loading}>
        {loading ? "Adding..." : "Watch Repo"}
      </Button>
      {error && <p className="text-sm text-red-600 w-full">{error}</p>}
    </form>
  );
}
