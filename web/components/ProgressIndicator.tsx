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
    <div className="flex items-center gap-3 text-sm text-gray-600">
      <span className="inline-block w-4 h-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
      <span>{status}</span>
    </div>
  );
}
