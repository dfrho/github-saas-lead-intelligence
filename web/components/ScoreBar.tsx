"use client";

interface ScoreBarProps {
  label: string;
  score: number | null;
  weight: string;
}

export function ScoreBar({ label, score, weight }: ScoreBarProps) {
  const pct = score ?? 0;

  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="font-medium text-foreground">{label}</span>
        <span className="font-mono text-xs text-muted-foreground tabular-nums">
          {weight} · {score ?? "—"}/100
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          data-testid="score-bar-fill"
          className="h-full rounded-full bg-gold transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
