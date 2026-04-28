import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LandingPage from "@/app/page";

// Next.js navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// Supabase client
vi.mock("@/lib/supabase", () => ({
  createClient: () => ({
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) },
  }),
}));

// API
vi.mock("@/lib/api", () => ({
  triggerReport: vi.fn(),
  fetchReportStatus: vi.fn(),
}));

import { triggerReport } from "@/lib/api";
const mockTrigger = triggerReport as ReturnType<typeof vi.fn>;

beforeEach(() => {
  mockTrigger.mockReset();
});

describe("LandingPage", () => {
  it("renders the heading and form", () => {
    render(<LandingPage />);
    expect(screen.getByText("Repolytics")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("e.g. stripe")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("e.g. stripe-python")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Analyze Repository/i })).toBeInTheDocument();
  });

  it("disables the button when owner or repo is empty", () => {
    render(<LandingPage />);
    const button = screen.getByRole("button", { name: /Analyze Repository/i });
    fireEvent.click(button);
    expect(mockTrigger).not.toHaveBeenCalled();
  });

  it("calls triggerReport with trimmed owner and repo on submit", async () => {
    mockTrigger.mockResolvedValue({ report_id: "test-id-123" });
    render(<LandingPage />);

    fireEvent.change(screen.getByPlaceholderText("e.g. stripe"), { target: { value: " stripe " } });
    fireEvent.change(screen.getByPlaceholderText("e.g. stripe-python"), { target: { value: " stripe-python " } });
    fireEvent.click(screen.getByRole("button", { name: /Analyze Repository/i }));

    await waitFor(() => expect(mockTrigger).toHaveBeenCalledWith("stripe", "stripe-python", null));
  });

  it("shows an error message when triggerReport rejects", async () => {
    mockTrigger.mockRejectedValue(new Error("Network error"));
    render(<LandingPage />);

    fireEvent.change(screen.getByPlaceholderText("e.g. stripe"), { target: { value: "stripe" } });
    fireEvent.change(screen.getByPlaceholderText("e.g. stripe-python"), { target: { value: "stripe-python" } });
    fireEvent.click(screen.getByRole("button", { name: /Analyze Repository/i }));

    await waitFor(() => expect(screen.getByText("Network error")).toBeInTheDocument());
  });

  it("shows the progress indicator after a successful trigger", async () => {
    mockTrigger.mockResolvedValue({ report_id: "test-id-123" });
    render(<LandingPage />);

    fireEvent.change(screen.getByPlaceholderText("e.g. stripe"), { target: { value: "stripe" } });
    fireEvent.change(screen.getByPlaceholderText("e.g. stripe-python"), { target: { value: "stripe-python" } });
    fireEvent.click(screen.getByRole("button", { name: /Analyze Repository/i }));

    await waitFor(() => expect(screen.getByText(/stripe\/stripe-python/)).toBeInTheDocument());
  });
});
