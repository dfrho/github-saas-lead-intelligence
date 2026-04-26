import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { NavBar } from "@/components/NavBar";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

const mockSignOut = vi.fn();
const mockGetSession = vi.fn();

vi.mock("@/lib/supabase", () => ({
  createClient: () => ({
    auth: {
      getSession: mockGetSession,
      signOut: mockSignOut,
    },
  }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockSignOut.mockResolvedValue({});
});

describe("NavBar", () => {
  it("renders site name, Account link, and Sign out button", async () => {
    mockGetSession.mockResolvedValue({ data: { session: null } });
    render(<NavBar />);
    expect(screen.getByText("GitHub Lead Intelligence")).toBeInTheDocument();
    expect(screen.getByText("Account")).toBeInTheDocument();
    expect(screen.getByText("Sign out")).toBeInTheDocument();
  });

  it("shows email when session is present", async () => {
    mockGetSession.mockResolvedValue({
      data: { session: { user: { email: "user@example.com" } } },
    });
    render(<NavBar />);
    await waitFor(() => expect(screen.getByText("user@example.com")).toBeInTheDocument());
  });

  it("does not show email when there is no session", async () => {
    mockGetSession.mockResolvedValue({ data: { session: null } });
    render(<NavBar />);
    await waitFor(() => expect(screen.queryByText("@")).not.toBeInTheDocument());
  });

  it("calls signOut and redirects to / on Sign out click", async () => {
    mockGetSession.mockResolvedValue({ data: { session: null } });
    render(<NavBar />);
    fireEvent.click(screen.getByText("Sign out"));
    await waitFor(() => {
      expect(mockSignOut).toHaveBeenCalledOnce();
      expect(mockPush).toHaveBeenCalledWith("/");
    });
  });

  it("site name links to /dashboard", () => {
    mockGetSession.mockResolvedValue({ data: { session: null } });
    render(<NavBar />);
    expect(screen.getByText("GitHub Lead Intelligence").closest("a")).toHaveAttribute("href", "/dashboard");
  });

  it("Account link points to /account", () => {
    mockGetSession.mockResolvedValue({ data: { session: null } });
    render(<NavBar />);
    expect(screen.getByText("Account").closest("a")).toHaveAttribute("href", "/account");
  });
});
