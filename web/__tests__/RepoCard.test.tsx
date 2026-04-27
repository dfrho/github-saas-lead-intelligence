import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { RepoCard } from "@/components/RepoCard";
import type { ReportSummary } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

const LATEST: ReportSummary = {
  id: "report-1",
  owner: "stripe",
  repo: "stripe-python",
  run_at: "2026-04-27T10:00:00Z",
  status: "complete",
  score_composite: 74,
  confidence_label: "Warm lead",
};

const OLDER: ReportSummary = {
  id: "report-2",
  owner: "stripe",
  repo: "stripe-python",
  run_at: "2026-04-20T10:00:00Z",
  status: "complete",
  score_composite: 61,
  confidence_label: "Warm lead",
};

const OLDEST: ReportSummary = {
  id: "report-3",
  owner: "stripe",
  repo: "stripe-python",
  run_at: "2026-04-13T10:00:00Z",
  status: "complete",
  score_composite: 45,
  confidence_label: "Lukewarm",
};

describe("RepoCard", () => {
  it("renders the label and owner/repo", () => {
    render(<RepoCard owner="stripe" repo="stripe-python" label="Stripe Python" lastChecked={null} reports={[]} />);
    expect(screen.getByText("Stripe Python")).toBeInTheDocument();
    expect(screen.getByText("stripe/stripe-python")).toBeInTheDocument();
  });

  it("shows 'Never checked' when lastChecked is null", () => {
    render(<RepoCard owner="stripe" repo="stripe-python" label="Stripe Python" lastChecked={null} reports={[]} />);
    expect(screen.getByText("Never checked")).toBeInTheDocument();
  });

  it("shows last checked date when provided", () => {
    render(<RepoCard owner="stripe" repo="stripe-python" label="Stripe Python" lastChecked="2026-04-27T10:00:00Z" reports={[]} />);
    expect(screen.getByText(/Last checked/)).toBeInTheDocument();
  });

  it("shows no score or View Report when there are no reports", () => {
    render(<RepoCard owner="stripe" repo="stripe-python" label="Stripe Python" lastChecked={null} reports={[]} />);
    expect(screen.queryByText(/View Report/)).not.toBeInTheDocument();
    expect(screen.queryByText(/\/100/)).not.toBeInTheDocument();
  });

  it("shows the latest score and confidence label", () => {
    render(<RepoCard owner="stripe" repo="stripe-python" label="Stripe Python" lastChecked={null} reports={[LATEST]} />);
    expect(screen.getByText("74/100")).toBeInTheDocument();
    expect(screen.getByText("Warm lead")).toBeInTheDocument();
  });

  it("links the card to the latest report", () => {
    render(<RepoCard owner="stripe" repo="stripe-python" label="Stripe Python" lastChecked={null} reports={[LATEST]} />);
    const link = screen.getByText("View Report →").closest("a");
    expect(link).toHaveAttribute("href", "/reports/report-1");
  });

  it("does not show Previous runs when there is only one report", () => {
    render(<RepoCard owner="stripe" repo="stripe-python" label="Stripe Python" lastChecked={null} reports={[LATEST]} />);
    expect(screen.queryByText("Previous runs")).not.toBeInTheDocument();
  });

  it("shows Previous runs section when there are multiple reports", () => {
    render(<RepoCard owner="stripe" repo="stripe-python" label="Stripe Python" lastChecked={null} reports={[LATEST, OLDER, OLDEST]} />);
    expect(screen.getByText("Previous runs")).toBeInTheDocument();
  });

  it("renders one history row per older report", () => {
    render(<RepoCard owner="stripe" repo="stripe-python" label="Stripe Python" lastChecked={null} reports={[LATEST, OLDER, OLDEST]} />);
    expect(screen.getByText("61/100")).toBeInTheDocument();
    expect(screen.getByText("45/100")).toBeInTheDocument();
  });

  it("each history row links to that report", () => {
    render(<RepoCard owner="stripe" repo="stripe-python" label="Stripe Python" lastChecked={null} reports={[LATEST, OLDER, OLDEST]} />);
    const links = screen.getAllByRole("link");
    const hrefs = links.map((l) => l.getAttribute("href"));
    expect(hrefs).toContain("/reports/report-2");
    expect(hrefs).toContain("/reports/report-3");
  });
});
