import { scoreColor, scoreBg, fmtPct, fmtMetric, formatDate } from "@/lib/utils";

describe("utils", () => {
  it("returns green for >= 80", () => {
    expect(scoreColor(85)).toContain("green");
  });

  it("returns yellow/orange/red for low scores", () => {
    expect(scoreColor(60)).toContain("yellow");
    expect(scoreColor(40)).toContain("orange");
    expect(scoreColor(20)).toContain("red");
  });

  it("scoreBg returns background class", () => {
    expect(scoreBg(85)).toContain("green");
  });

  it("fmtPct rounds", () => {
    expect(fmtPct(85.6)).toBe("86%");
  });

  it("fmtMetric handles numbers", () => {
    expect(fmtMetric(0.123)).toBe("0.123");
    expect(fmtMetric(NaN)).toBe("—");
  });

  it("formatDate returns something parseable", () => {
    const out = formatDate(new Date().toISOString());
    expect(out.length).toBeGreaterThan(0);
  });
});
