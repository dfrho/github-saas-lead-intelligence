import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AccountPage from "@/app/account/page";

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

vi.mock("@/lib/api", () => ({
  fetchProfile: vi.fn(),
  upsertProfile: vi.fn(),
}));

import { fetchProfile, upsertProfile } from "@/lib/api";
const mockFetchProfile = fetchProfile as ReturnType<typeof vi.fn>;
const mockUpsertProfile = upsertProfile as ReturnType<typeof vi.fn>;

const SESSION = {
  access_token: "tok-123",
  user: { email: "user@example.com" },
};

// Wait for the account form to be visible — unique to AccountPage, not in NavBar
async function waitForLoaded() {
  await waitFor(() => screen.getByPlaceholderText("e.g. Acme Corp"));
}

// The page has two "Sign out" buttons: one in NavBar, one in the page body.
// The page-body button is the second one.
function getPageSignOutButton() {
  return screen.getAllByRole("button", { name: /Sign out/i })[1];
}

beforeEach(() => {
  vi.clearAllMocks();
  mockSignOut.mockResolvedValue({});
  mockUpsertProfile.mockResolvedValue({});
});

describe("AccountPage", () => {
  it("redirects to /login when there is no session", async () => {
    mockGetSession.mockResolvedValue({ data: { session: null } });
    render(<AccountPage />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/login?next=/account"));
  });

  it("renders nothing while session is loading", () => {
    mockGetSession.mockReturnValue(new Promise(() => {}));
    const { container } = render(<AccountPage />);
    expect(container).toBeEmptyDOMElement();
  });

  it("displays the user email read-only", async () => {
    mockGetSession.mockResolvedValue({ data: { session: SESSION } });
    mockFetchProfile.mockResolvedValue({ company_name: null, work_domain: null });
    render(<AccountPage />);
    await waitForLoaded();
    // The page-body email is in a <p> tag; NavBar email is in a <span>
    const emails = screen.getAllByText("user@example.com");
    expect(emails.length).toBeGreaterThanOrEqual(1);
    expect(emails.some((el) => el.tagName === "P")).toBe(true);
  });

  it("pre-fills company name and work domain from profile", async () => {
    mockGetSession.mockResolvedValue({ data: { session: SESSION } });
    mockFetchProfile.mockResolvedValue({ company_name: "Acme Corp", work_domain: "acme.com" });
    render(<AccountPage />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText("e.g. Acme Corp")).toHaveValue("Acme Corp");
      expect(screen.getByPlaceholderText("e.g. acme.com")).toHaveValue("acme.com");
    });
  });

  it("starts with empty fields when profile fetch fails", async () => {
    mockGetSession.mockResolvedValue({ data: { session: SESSION } });
    mockFetchProfile.mockRejectedValue(new Error("404"));
    render(<AccountPage />);
    await waitForLoaded();
    expect(screen.getByPlaceholderText("e.g. Acme Corp")).toHaveValue("");
    expect(screen.getByPlaceholderText("e.g. acme.com")).toHaveValue("");
  });

  it("calls upsertProfile with current field values on save", async () => {
    mockGetSession.mockResolvedValue({ data: { session: SESSION } });
    mockFetchProfile.mockResolvedValue({ company_name: "", work_domain: "" });
    render(<AccountPage />);
    await waitForLoaded();

    fireEvent.change(screen.getByPlaceholderText("e.g. Acme Corp"), { target: { value: "Globex" } });
    fireEvent.change(screen.getByPlaceholderText("e.g. acme.com"), { target: { value: "globex.com" } });
    fireEvent.click(screen.getByRole("button", { name: /Save changes/i }));

    await waitFor(() =>
      expect(mockUpsertProfile).toHaveBeenCalledWith("tok-123", "Globex", "globex.com")
    );
  });

  it("shows 'Saved' confirmation after successful save", async () => {
    mockGetSession.mockResolvedValue({ data: { session: SESSION } });
    mockFetchProfile.mockResolvedValue({ company_name: "", work_domain: "" });
    render(<AccountPage />);
    await waitForLoaded();

    fireEvent.click(screen.getByRole("button", { name: /Save changes/i }));
    await waitFor(() => expect(screen.getByText("Saved")).toBeInTheDocument());
  });

  it("hides 'Saved' confirmation after 3 seconds", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockGetSession.mockResolvedValue({ data: { session: SESSION } });
    mockFetchProfile.mockResolvedValue({ company_name: "", work_domain: "" });
    render(<AccountPage />);

    // Flush session + profile promises without triggering long timers
    await act(async () => { await vi.advanceTimersByTimeAsync(100); });
    await waitForLoaded();

    fireEvent.click(screen.getByRole("button", { name: /Save changes/i }));

    // Flush the save promise (100ms << 3000ms, so hide timer not yet fired)
    await act(async () => { await vi.advanceTimersByTimeAsync(100); });
    expect(screen.getByText("Saved")).toBeInTheDocument();

    // Now fire the 3-second hide timer
    act(() => { vi.advanceTimersByTime(3000); });
    expect(screen.queryByText("Saved")).not.toBeInTheDocument();

    vi.useRealTimers();
  });

  it("shows an error message when save fails", async () => {
    mockGetSession.mockResolvedValue({ data: { session: SESSION } });
    mockFetchProfile.mockResolvedValue({ company_name: "", work_domain: "" });
    mockUpsertProfile.mockRejectedValue(new Error("Server error"));
    render(<AccountPage />);
    await waitForLoaded();

    fireEvent.click(screen.getByRole("button", { name: /Save changes/i }));
    await waitFor(() => expect(screen.getByText("Server error")).toBeInTheDocument());
  });

  it("calls signOut and redirects to / on Sign out click", async () => {
    mockGetSession.mockResolvedValue({ data: { session: SESSION } });
    mockFetchProfile.mockResolvedValue({ company_name: null, work_domain: null });
    render(<AccountPage />);
    await waitForLoaded();

    fireEvent.click(getPageSignOutButton());
    await waitFor(() => {
      expect(mockSignOut).toHaveBeenCalled();
      expect(mockPush).toHaveBeenCalledWith("/");
    });
  });
});
