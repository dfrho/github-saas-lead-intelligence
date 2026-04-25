"use client";

interface ScoreBarProps {
  label: string;
  score: number | null;
  weight: string;
}

export function ScoreBar({ label, score, weight }: ScoreBarProps) {
  const pct = score ?? 0;
  const color =
    pct >= 80 ? "bg-red-500" :
    pct >= 60 ? "bg-orange-400" :
    pct >= 40 ? "bg-yellow-400" :
    "bg-gray-300";

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-700 font-medium">{label}</span>
        <span className="text-gray-500">{weight} · {score ?? "—"}/100</span>
      </div>
      <div className="h-2 w-full rounded-full bg-gray-100">
        <div
          className={`h-2 rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
