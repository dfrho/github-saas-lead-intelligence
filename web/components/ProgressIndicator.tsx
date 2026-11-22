"use client";

import { useEffect, useState } from "react";
import { fetchReportStatus } from "@/lib/api";

const DONE = "complete";

interface ProgressIndicatorProps {
  reportId: string;
  onComplete: () => void;
}

export function ProgressIndicator({ reportId, onComplete }: ProgressIndicatorProps) {
  const [status, setStatus] = useState("Initializing...");

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      while (!cancelled) {
        try {
          const data = await fetchReportStatus(reportId);
          if (cancelled) break;
          setStatus(data.status);
          if (data.status === DONE || data.status.startsWith("error")) {
            onComplete();
            break;
          }
        } catch {
          // network hiccup — keep polling
        }
        await new Promise((r) => setTimeout(r, 3000));
      }
    }

    poll();
    return () => { cancelled = true; };
  }, [reportId, onComplete]);

  return (
    <div className="flex items-center gap-3 text-sm text-muted-foreground" role="status" aria-live="polite">
      <span
        className="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-foreground border-t-transparent"
        aria-hidden="true"
      />
      <span className="font-mono text-[13px]">{status}</span>
    </div>
  );
}
