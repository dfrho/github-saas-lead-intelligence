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

  it("applies red color class for score >= 80", () => {
    const { container } = render(<ScoreBar label="X" score={80} weight="25%" />);
    const bar = container.querySelector(".bg-red-500");
    expect(bar).toBeInTheDocument();
    expect(bar).toHaveStyle({ width: "80%" });
  });

  it("applies orange color class for score 60–79", () => {
    const { container } = render(<ScoreBar label="X" score={65} weight="25%" />);
    expect(container.querySelector(".bg-orange-400")).toBeInTheDocument();
  });

  it("applies yellow color class for score 40–59", () => {
    const { container } = render(<ScoreBar label="X" score={50} weight="25%" />);
    expect(container.querySelector(".bg-yellow-400")).toBeInTheDocument();
  });

  it("applies gray color class for score < 40", () => {
    const { container } = render(<ScoreBar label="X" score={20} weight="25%" />);
    expect(container.querySelector(".bg-gray-300")).toBeInTheDocument();
  });

  it("renders a zero-width bar when score is null", () => {
    const { container } = render(<ScoreBar label="X" score={null} weight="20%" />);
    const bar = container.querySelector(".bg-gray-300");
    expect(bar).toHaveStyle({ width: "0%" });
  });
});
