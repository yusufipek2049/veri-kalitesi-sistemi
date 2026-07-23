import { describe, expect, it } from "vitest";
import { reportSummaryFromApi, type ReportSummaryApiResponse } from "./model";

describe("report model", () => {
  it("ondalık skorları dönüştürür, eksik ve teknik skorları null bırakır", () => {
    const summary = reportSummaryFromApi(fixture());

    expect(summary.averageScore).toBe(87.1);
    expect(summary.rows[0].scoreValue).toBe(91.8);
    expect(summary.rows[1]).toMatchObject({
      scoreStatus: "NOT_CALCULATED_TECHNICAL_ERROR",
      scoreValue: null,
    });
  });
});

function fixture(): ReportSummaryApiResponse {
  return {
    api_version: "v1",
    data_origin: "synthetic-test",
    correlation_id: "report-model",
    report_type: "SUMMARY",
    created_at: "2026-07-23T12:00:00Z",
    period_start: "2026-06-23T12:00:00Z",
    period_end: "2026-07-23T12:00:00Z",
    source_count: 2,
    calculated_source_count: 1,
    average_score: "87.10",
    policy_version: "REPORT_V1",
    masking_mode: "AGGREGATED_ONLY",
    rows: [
      {
        source_id: "source-a",
        score_value: "91.80",
        score_status: "CALCULATED",
        level: "GOOD",
        calculated_at: "2026-07-23T11:00:00Z",
      },
      {
        source_id: "source-b",
        score_value: null,
        score_status: "NOT_CALCULATED_TECHNICAL_ERROR",
        level: null,
        calculated_at: "2026-07-23T10:00:00Z",
      },
    ],
  };
}
