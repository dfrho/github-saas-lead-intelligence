import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ProgressIndicator } from "@/components/ProgressIndicator";

vi.mock("@/lib/api", () => ({
  fetchReportStatus: vi.fn(),
}));

import { fetchReportStatus } from "@/lib/api";
const mockFetch = fetchReportStatus as ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.useFakeTimers();
  mockFetch.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("ProgressIndicator", () => {
  it("shows initial Initializing... status", () => {
    mockFetch.mockResolvedValue({ status: "Fetching repository activity..." });
    render(<ProgressIndicator reportId="abc" onComplete={() => {}} />);
    expect(screen.getByText("Initializing...")).toBeInTheDocument();
  });

  it("updates status text after first poll", async () => {
    mockFetch.mockResolvedValue({ status: "Analyzing commits..." });
    render(<ProgressIndicator reportId="abc" onComplete={() => {}} />);
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByText("Analyzing commits...")).toBeInTheDocument();
  });

  it("calls onComplete when status is 'complete'", async () => {
    const onComplete = vi.fn();
    mockFetch.mockResolvedValue({ status: "complete" });
    render(<ProgressIndicator reportId="abc" onComplete={onComplete} />);
    await act(async () => { await Promise.resolve(); });
    expect(onComplete).toHaveBeenCalledOnce();
  });

  it("calls onComplete when status starts with 'error'", async () => {
    const onComplete = vi.fn();
    mockFetch.mockResolvedValue({ status: "error: GitHub API rate limited" });
    render(<ProgressIndicator reportId="abc" onComplete={onComplete} />);
    await act(async () => { await Promise.resolve(); });
    expect(onComplete).toHaveBeenCalledOnce();
  });

  it("renders the spinner element", () => {
    mockFetch.mockResolvedValue({ status: "Initializing..." });
    const { container } = render(<ProgressIndicator reportId="abc" onComplete={() => {}} />);
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });
});
