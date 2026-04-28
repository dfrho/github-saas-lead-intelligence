import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ScoreBar } from "@/components/ScoreBar";

describe("ScoreBar", () => {
  it("renders the label and weight", () => {
    render(<ScoreBar label="Activity" score={75} weight="25%" />);
    expect(screen.getByText("Activity")).toBeInTheDocument();
    expect(screen.getByText("25% · 75/100")).toBeInTheDocument();
  });

  it("shows em-dash when score is null", () => {
    render(<ScoreBar label="Growth Signals" score={null} weight="15%" />);
    expect(screen.getByText("15% · —/100")).toBeInTheDocument();
  });

  it("applies blue fill for score >= 80", () => {
    render(<ScoreBar label="X" score={80} weight="25%" />);
    const bar = screen.getByTestId("score-bar-fill");
    expect(bar).toBeInTheDocument();
    expect(bar).toHaveStyle({ width: "80%", backgroundColor: "#343ced" });
  });

  it("applies lime fill for score 60–79", () => {
    render(<ScoreBar label="X" score={65} weight="25%" />);
    const bar = screen.getByTestId("score-bar-fill");
    expect(bar).toHaveStyle({ backgroundColor: "#d8fd49" });
  });

  it("applies amber fill for score 40–59", () => {
    render(<ScoreBar label="X" score={50} weight="25%" />);
    const bar = screen.getByTestId("score-bar-fill");
    expect(bar).toHaveStyle({ backgroundColor: "#f59e0b" });
  });

  it("applies gray fill for score < 40", () => {
    render(<ScoreBar label="X" score={20} weight="25%" />);
    const bar = screen.getByTestId("score-bar-fill");
    expect(bar).toHaveStyle({ backgroundColor: "#d1d5db" });
  });

  it("renders a zero-width bar when score is null", () => {
    render(<ScoreBar label="X" score={null} weight="20%" />);
    const bar = screen.getByTestId("score-bar-fill");
    expect(bar).toHaveStyle({ width: "0%" });
  });
});
