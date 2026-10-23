import { describe, it, expect } from "vitest";
import { safeNext } from "@/lib/safeNext";

describe("safeNext", () => {
  it("keeps same-origin paths, query and hash", () => {
    expect(safeNext("/reports/abc?x=1#top")).toBe("/reports/abc?x=1#top");
    expect(safeNext("/dashboard")).toBe("/dashboard");
  });

  it("falls back when next is missing", () => {
    expect(safeNext(null)).toBe("/dashboard");
    expect(safeNext(undefined)).toBe("/dashboard");
    expect(safeNext("")).toBe("/dashboard");
  });

  it.each([
    "@evil.example",
    ".evil.example",
    "evil.example",
    "https://evil.example",
    "//evil.example",
    "/\\evil.example",
    "/\tevil",
    "javascript:alert(1)",
  ])("rejects off-site target %s", (target) => {
    expect(safeNext(target)).toBe("/dashboard");
  });

  it("never changes the host when appended to an origin", () => {
    const origin = "https://github-saas-lead-intelligence.vercel.app";
    for (const target of ["@evil.example", ".evil.example", "//evil.example", "/ok"]) {
      expect(new URL(`${origin}${safeNext(target)}`).host).toBe(new URL(origin).host);
    }
  });
});
