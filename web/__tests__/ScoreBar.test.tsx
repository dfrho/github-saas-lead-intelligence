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

  it.each([80, 65, 50, 20])("sizes the fill to the score (%i)", (score) => {
    render(<ScoreBar label="X" score={score} weight="25%" />);
    expect(screen.getByTestId("score-bar-fill")).toHaveStyle({ width: `${score}%` });
  });

  it("uses the brand fill color at every score", () => {
    const { rerender } = render(<ScoreBar label="X" score={90} weight="25%" />);
    expect(screen.getByTestId("score-bar-fill")).toHaveClass("bg-gold");
    rerender(<ScoreBar label="X" score={10} weight="25%" />);
    expect(screen.getByTestId("score-bar-fill")).toHaveClass("bg-gold");
  });

  it("renders a zero-width bar when score is null", () => {
    render(<ScoreBar label="X" score={null} weight="20%" />);
    const bar = screen.getByTestId("score-bar-fill");
    expect(bar).toHaveStyle({ width: "0%" });
  });
});
