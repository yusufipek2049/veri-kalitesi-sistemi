export type ReportState =
  | "normal"
  | "loading"
  | "empty"
  | "error"
  | "unauthorized"
  | "long-content";

export interface ReportSummaryRow {
  sourceId: string;
  scoreValue: number | null;
  scoreStatus: string;
  level: string | null;
  calculatedAt: string;
}

export interface ReportSummary {
  reportType: string;
  createdAt: string;
  periodStart: string;
  periodEnd: string;
  sourceCount: number;
  calculatedSourceCount: number;
  averageScore: number | null;
  policyVersion: string;
  maskingMode: string;
  rows: ReportSummaryRow[];
}

export interface ReportSummaryApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  report_type: string;
  created_at: string;
  period_start: string;
  period_end: string;
  source_count: number;
  calculated_source_count: number;
  average_score: string | null;
  policy_version: string;
  masking_mode: string;
  rows: Array<{
    source_id: string;
    score_value: string | null;
    score_status: string;
    level: string | null;
    calculated_at: string;
  }>;
}

export const syntheticReportSummary: ReportSummary = {
  reportType: "SUMMARY",
  createdAt: "2026-07-23T12:00:00Z",
  periodStart: "2026-06-23T12:00:00Z",
  periodEnd: "2026-07-23T12:00:00Z",
  sourceCount: 4,
  calculatedSourceCount: 2,
  averageScore: 87.1,
  policyVersion: "DEVELOPMENT_REPORT_POLICY_V1",
  maskingMode: "AGGREGATED_ONLY",
  rows: [
    {
      sourceId: "source-core-banking",
      scoreValue: 91.8,
      scoreStatus: "CALCULATED",
      level: "GOOD",
      calculatedAt: "2026-07-23T11:00:00Z",
    },
    {
      sourceId: "source-customer-file",
      scoreValue: 82.4,
      scoreStatus: "PARTIAL",
      level: "ACCEPTABLE",
      calculatedAt: "2026-07-23T10:00:00Z",
    },
    {
      sourceId: "source-risk-mart",
      scoreValue: null,
      scoreStatus: "NO_DATA",
      level: null,
      calculatedAt: "2026-07-23T09:00:00Z",
    },
    {
      sourceId: "source-regulatory-api",
      scoreValue: null,
      scoreStatus: "NOT_CALCULATED_TECHNICAL_ERROR",
      level: null,
      calculatedAt: "2026-07-23T08:00:00Z",
    },
  ],
};

export function reportSummaryFromApi(response: ReportSummaryApiResponse): ReportSummary {
  return {
    reportType: response.report_type,
    createdAt: response.created_at,
    periodStart: response.period_start,
    periodEnd: response.period_end,
    sourceCount: response.source_count,
    calculatedSourceCount: response.calculated_source_count,
    averageScore: response.average_score === null ? null : Number(response.average_score),
    policyVersion: response.policy_version,
    maskingMode: response.masking_mode,
    rows: response.rows.map((row) => ({
      sourceId: row.source_id,
      scoreValue: row.score_value === null ? null : Number(row.score_value),
      scoreStatus: row.score_status,
      level: row.level,
      calculatedAt: row.calculated_at,
    })),
  };
}
