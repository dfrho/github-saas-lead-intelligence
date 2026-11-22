"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  FolderGit2,
  UserRound,
  LogOut,
  Menu,
  X,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { createClient } from "@/lib/supabase";
import { cn } from "@/lib/utils";
import { LogoMark } from "@/components/Logo";

function subscribeNoop() {
  return () => {};
}

const COLLAPSED_KEY = "repolytics.sidebarCollapsed";

function readCollapsed(): boolean {
  try {
    return typeof window !== "undefined" && window.localStorage.getItem(COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

const LINKS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/repos", label: "Watched repos", icon: FolderGit2 },
  { href: "/account", label: "Account", icon: UserRound },
];

/**
 * App navigation. A fixed-width sidebar from the md breakpoint up; below it,
 * a top bar whose links open from a menu button. Every item renders once so
 * the same markup serves both layouts.
 */
export function NavBar() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  // Desktop only: icon rail instead of the full sidebar, remembered per browser
  const [collapsed, setCollapsed] = useState(readCollapsed);

  function toggleCollapsed() {
    setCollapsed((c) => {
      const next = !c;
      try {
        window.localStorage.setItem(COLLAPSED_KEY, next ? "1" : "0");
      } catch {
        // storage unavailable: the choice just won't persist
      }
      return next;
    });
  }

  // Hidden visually on the desktop rail, still read by screen readers
  const railHide = collapsed ? "md:sr-only" : "";
  // Current path for the active-link highlight. Read from location so the
  // nav keeps working wherever next/navigation is mocked; "" on the server.
  const path = useSyncExternalStore(
    subscribeNoop,
    () => window.location.pathname,
    () => ""
  );

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data: { session } }) => {
      setEmail(session?.user?.email ?? null);
    });
  }, []);

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
  }

  return (
    // The wrapper paints the sidebar column (background and border) down the
    // full page height on md+. On phones it is display:contents, so the nav
    // itself is the sticky top bar.
    <div
      className={cn(
        "contents md:block md:shrink-0 md:border-r md:border-border md:bg-card md:transition-[width]",
        collapsed ? "md:w-16" : "md:w-60"
      )}
    >
    <nav
      aria-label="Main"
      className="sticky top-0 z-30 border-b border-border bg-card md:flex md:h-screen md:flex-col md:border-b-0 md:bg-transparent"
    >
      <div
        className={cn(
          "flex h-14 items-center justify-between px-4 md:h-16",
          collapsed ? "md:justify-center md:px-0" : "md:px-5"
        )}
      >
        <a
          href="/dashboard"
          className="inline-flex items-center gap-2 font-display text-[17px] font-bold tracking-tight text-foreground"
        >
          <LogoMark />
          <span className={railHide}>Repolytics</span>
        </a>
        <button
          type="button"
          className="inline-flex h-11 w-11 items-center justify-center rounded-md text-foreground hover:bg-accent md:hidden"
          aria-expanded={open}
          aria-controls="main-nav-links"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? <X className="h-5 w-5" aria-hidden="true" /> : <Menu className="h-5 w-5" aria-hidden="true" />}
        </button>
      </div>

      <div
        id="main-nav-links"
        className={cn(
          "flex-col gap-1 px-3 pb-4 md:flex md:flex-1 md:pb-5",
          open ? "flex" : "hidden"
        )}
      >
        {LINKS.map(({ href, label, icon: Icon }) => {
          const active = path === href || path.startsWith(`${href}/`);
          return (
            <a
              key={href}
              href={href}
              title={collapsed ? label : undefined}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex h-11 items-center gap-3 rounded-md px-3 text-sm transition-colors md:h-10",
                collapsed && "md:justify-center md:px-0",
                active
                  ? "bg-accent font-medium text-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className={railHide}>{label}</span>
            </a>
          );
        })}

        <div className="mt-3 border-t border-border pt-3 md:mt-auto">
          {email && (
            <span
              className={cn("block truncate px-3 pb-2 text-xs text-muted-foreground", collapsed && "md:hidden")}
              title={email}
            >
              {email}
            </span>
          )}
          <button
            type="button"
            onClick={toggleCollapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className={cn(
              "hidden h-10 w-full items-center gap-3 rounded-md px-3 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground md:flex",
              collapsed && "md:justify-center md:px-0"
            )}
          >
            {collapsed ? (
              <PanelLeftOpen className="h-4 w-4 shrink-0" aria-hidden="true" />
            ) : (
              <PanelLeftClose className="h-4 w-4 shrink-0" aria-hidden="true" />
            )}
            <span className={railHide}>Collapse</span>
          </button>
          <button
            type="button"
            onClick={handleSignOut}
            title={collapsed ? "Sign out" : undefined}
            className={cn(
              "flex h-11 w-full items-center gap-3 rounded-md px-3 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground md:h-10",
              collapsed && "md:justify-center md:px-0"
            )}
          >
            <LogOut className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span className={railHide}>Sign out</span>
          </button>
        </div>
      </div>
    </nav>
    </div>
  );
}
