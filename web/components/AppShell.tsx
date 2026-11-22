import { NavBar } from "@/components/NavBar";
import { cn } from "@/lib/utils";

interface AppShellProps {
  children: React.ReactNode;
  /** Max width of the content column. Defaults to a wide dashboard column. */
  width?: "narrow" | "default" | "wide";
  className?: string;
}

const WIDTHS = {
  narrow: "max-w-2xl",
  default: "max-w-4xl",
  wide: "max-w-6xl",
};

/** Signed-in page frame: navigation plus a padded, centered content column. */
export function AppShell({ children, width = "wide", className }: AppShellProps) {
  // The md+ background paints the sidebar column (white + 1px border) down the
  // full page height, so the sticky nav never leaves a gap below it.
  return (
    <div className="flex min-h-screen flex-col bg-background md:flex-row md:bg-[linear-gradient(to_right,var(--card)_15rem,var(--border)_15rem,var(--border)_calc(15rem+1px),var(--background)_calc(15rem+1px))]">
      <NavBar />
      <main className="min-w-0 flex-1">
        <div className={cn("mx-auto w-full px-4 py-8 sm:px-6 md:px-8 md:py-10", WIDTHS[width], className)}>
          {children}
        </div>
      </main>
    </div>
  );
}

/** Page title row with optional actions; wraps on small screens. */
export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="space-y-1">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground sm:text-[28px]">
          {title}
        </h1>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
