import { describe, expect, it } from "vitest";
import type { DashboardOverview } from "./model";
import { createTrendTooltipFormatter } from "./trendTooltip";

const colors = {
  critical: "#c62828",
  success: "#2e7d32",
  muted: "#5b6574",
  chipBackground: "#eef1f5",
};

function periods(change: number | null = 2.4): DashboardOverview["trend"]["periods"] {
  return [{
    periodStart: "2026-08-01T00:00:00Z",
    periodEnd: "2026-08-07T23:59:59Z",
    observations: [{
      qualityScoreId: "score-1",
      scopeType: "ENTERPRISE",
      scopeId: null,
      scoreValue: 84.2,
      scoreStatus: "CALCULATED",
      level: "GOOD",
      calculatedAt: "2026-08-08T00:00:00Z",
      comparisonStatus: "NOT_COMPARABLE",
      comparisonReasonCodes: ["POLICY_VERSION_CHANGED", "NON_OFFICIAL_RESULT"],
      change,
      versionBoundary: true,
      policyVersion: "v2",
    }],
  }];
}

describe("createTrendTooltipFormatter", () => {
  it("renders the period range, score level, status, signed change and comparison reasons", () => {
    const html = createTrendTooltipFormatter(periods(), colors)([{ dataIndex: 0, value: 84.2 }]);

    expect(html).toContain("01.08 – 08.08");
    expect(html).toContain("Skor: <strong>84.2</strong>");
    expect(html).toContain(">GOOD</span>");
    expect(html).toContain("Durum: Hesaplandı");
    expect(html).toContain('color:#2e7d32">+2.4</strong>');
    expect(html).toContain("Karşılaştırma: Karşılaştırılamaz");
    expect(html).toContain("POLICY_VERSION_CHANGED, NON_OFFICIAL_RESULT");
  });

  it("uses the critical color for a negative change", () => {
    const html = createTrendTooltipFormatter(periods(-1.6), colors)([{ dataIndex: 0 }]);

    expect(html).toContain('color:#c62828">-1.6</strong>');
  });

  it("returns an empty tooltip for invalid formatter parameters", () => {
    const formatter = createTrendTooltipFormatter(periods(), colors);

    expect(formatter([])).toBe("");
    expect(formatter([{ dataIndex: 9 }])).toBe("");
  });

  it("escapes source names, policy versions and reason codes before producing HTML", () => {
    const fixture = periods();
    fixture[0].observations[0].policyVersion = '<script>alert("policy")</script>';
    fixture[0].observations[0].comparisonReasonCodes = ['<img src=x onerror="reason">'];
    fixture[0].observations.push({
      ...fixture[0].observations[0],
      qualityScoreId: "source-score",
      scopeType: "SOURCE",
      scopeId: "source-a",
      scoreValue: 73.1,
      versionBoundary: false,
      policyVersion: null,
    });
    const formatter = createTrendTooltipFormatter(
      fixture,
      colors,
      new Map([["source-a", '<img src=x onerror="source">']]),
    );

    const html = formatter([{ dataIndex: 0, seriesId: "source:source-a" }]);

    expect(html).not.toContain("<script>");
    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;script&gt;alert(&quot;policy&quot;)&lt;/script&gt;");
    expect(html).toContain("&lt;img src=x onerror=&quot;source&quot;&gt;: 73.1");
    expect(html).toContain("&lt;img src=x onerror=&quot;reason&quot;&gt;");
  });

  it("resolves duplicate display names through the source series id", () => {
    const fixture = periods();
    fixture[0].observations.push(
      { ...fixture[0].observations[0], qualityScoreId: "source-a-score", scopeType: "SOURCE", scopeId: "source-a", scoreValue: 61 },
      { ...fixture[0].observations[0], qualityScoreId: "source-b-score", scopeType: "SOURCE", scopeId: "source-b", scoreValue: 79 },
    );
    const names = new Map([["source-a", "Aynı Kaynak"], ["source-b", "Aynı Kaynak"]]);

    const html = createTrendTooltipFormatter(fixture, colors, names)([
      { dataIndex: 0, seriesId: "source:source-b", seriesName: "Aynı Kaynak" },
    ]);

    expect(html).toContain("Aynı Kaynak: 79.0");
    expect(html).not.toContain("Aynı Kaynak: 61.0");
  });
});
