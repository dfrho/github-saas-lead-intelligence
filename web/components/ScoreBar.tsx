"use client";

interface ScoreBarProps {
  label: string;
  score: number | null;
  weight: string;
}

export function ScoreBar({ label, score, weight }: ScoreBarProps) {
  const pct = score ?? 0;

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="font-medium text-foreground">{label}</span>
        <span className="text-muted-foreground">{weight} · {score ?? "—"}/100</span>
      </div>
      <div className="h-2.5 w-full rounded-full bg-muted overflow-hidden">
        <div
          data-testid="score-bar-fill"
          className="h-full rounded-full bg-gold transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
