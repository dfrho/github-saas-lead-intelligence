"use client";

interface ScoreBarProps {
  label: string;
  score: number | null;
  weight: string;
}

export function ScoreBar({ label, score, weight }: ScoreBarProps) {
  const pct = score ?? 0;
  const barColor =
    pct >= 80 ? "#343ced" :
    pct >= 60 ? "#d8fd49" :
    pct >= 40 ? "#f59e0b" :
    "#d1d5db";

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="font-medium" style={{ color: "#484848" }}>{label}</span>
        <span style={{ color: "#484848", opacity: 0.5 }}>{weight} · {score ?? "—"}/100</span>
      </div>
      <div className="h-2 w-full rounded-full" style={{ backgroundColor: "#f3f4f6" }}>
        <div
          data-testid="score-bar-fill"
          className="h-2 rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: barColor }}
        />
      </div>
    </div>
  );
}
