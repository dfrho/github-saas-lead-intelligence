import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// Minimal component that mirrors the copy button in the report page
function OutreachSection({ text }: { text: string }) {
  const [copied, setCopied] = React.useState(false);
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <h3>Outreach Angle</h3>
        <button
          onClick={() => {
            navigator.clipboard.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 5000);
          }}
          title="Copy outreach angle"
        >
          Copy
        </button>
        {copied && <span>Outreach copied</span>}
      </div>
      <p>{text}</p>
    </div>
  );
}

import React from "react";

beforeEach(() => {
  vi.useFakeTimers();
  Object.assign(navigator, {
    clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
  });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("Outreach copy button", () => {
  it("shows 'Outreach copied' after clicking the copy button", async () => {
    render(<OutreachSection text="Call them about CI/CD." />);

    expect(screen.queryByText("Outreach copied")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTitle("Copy outreach angle"));
    expect(screen.getByText("Outreach copied")).toBeInTheDocument();
  });

  it("writes the outreach text to the clipboard", () => {
    render(<OutreachSection text="Call them about CI/CD." />);
    fireEvent.click(screen.getByTitle("Copy outreach angle"));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("Call them about CI/CD.");
  });

  it("hides the confirmation after 5 seconds", () => {
    render(<OutreachSection text="Call them about CI/CD." />);
    fireEvent.click(screen.getByTitle("Copy outreach angle"));
    expect(screen.getByText("Outreach copied")).toBeInTheDocument();

    act(() => { vi.advanceTimersByTime(5000); });
    expect(screen.queryByText("Outreach copied")).not.toBeInTheDocument();
  });
});
