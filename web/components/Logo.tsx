import { cn } from "@/lib/utils";

/**
 * Repolytics mark: three commit nodes climbing to the upper right, read as
 * "activity becoming a signal". Inherits color from the surrounding text so
 * it flips with the light and dark themes.
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={cn("h-6 w-6 shrink-0", className)}
      aria-hidden="true"
      focusable="false"
    >
      <rect width="24" height="24" rx="6" fill="currentColor" />
      <path
        d="M6.5 16.5 L11.5 12.5 L17.5 7"
        fill="none"
        stroke="var(--background)"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="6.5" cy="16.5" r="2" fill="var(--background)" />
      <circle cx="11.5" cy="12.5" r="2" fill="var(--background)" />
      <circle cx="17.5" cy="7" r="2.25" fill="var(--gold)" />
    </svg>
  );
}
