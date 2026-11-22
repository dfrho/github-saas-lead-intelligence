import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SWRConfig } from "swr";
import DashboardPage from "@/app/dashboard/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/supabase", () => ({
  createClient: () => ({
    auth: {
      getSession: () =>
        Promise.resolve({ data: { session: { access_token: "tok", user: { email: "a@b.co" } } } }),
      signOut: vi.fn(),
    },
  }),
}));

vi.mock("@/lib/api", () => ({
  fetchRepos: vi.fn(),
  fetchReports: vi.fn(),
}));

import { fetchRepos, fetchReports } from "@/lib/api";
const mockFetchRepos = fetchRepos as ReturnType<typeof vi.fn>;
const mockFetchReports = fetchReports as ReturnType<typeof vi.fn>;

function renderPage() {
  return render(
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      <DashboardPage />
    </SWRConfig>
  );
}

describe("DashboardPage loading state", () => {
  beforeEach(() => {
    mockFetchRepos.mockReset();
    mockFetchReports.mockReset();
  });

  it("shows skeletons, not zeros or the empty state, while data loads", async () => {
    mockFetchRepos.mockReturnValue(new Promise(() => {}));
    mockFetchReports.mockReturnValue(new Promise(() => {}));
    renderPage();

    expect(await screen.findByRole("status", { name: "Loading watched repos" })).toBeInTheDocument();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
    expect(screen.queryByText("No repos watched yet.")).not.toBeInTheDocument();
  });

  it("shows real counts once data arrives", async () => {
    mockFetchRepos.mockResolvedValue([]);
    mockFetchReports.mockResolvedValue([]);
    renderPage();

    expect(await screen.findByText("No repos watched yet.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText("0")).toHaveLength(3));
    expect(screen.queryByRole("status", { name: "Loading watched repos" })).not.toBeInTheDocument();
  });
});
