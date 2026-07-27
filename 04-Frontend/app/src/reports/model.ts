export type ReportState =
  | "normal"
  | "loading"
  | "empty"
  | "error"
  | "unauthorized"
  | "long-content";

export type ReportFormat = "PDF" | "XLSX" | "CSV";
export type ReportType = "SUMMARY" | "DETAIL" | "TREND" | "UNIT" | "OWNER" | "CRITICAL_DATA" | "ISSUE_PERFORMANCE";
export type ReportStatus = "QUEUED" | "RUNNING" | "READY" | "FAILED" | "EXPIRED";

export interface ReportRequest {
  report_type: ReportType;
  format: ReportFormat;
  parameters: Record<string, unknown>;
  reason_code: string;
  sensitivity_level: string | null;
}

export interface ReportItem {
  report_id: string;
  report_type: string;
  format: string;
  status: ReportStatus;
  file_size: number | null;
  expires_at: string | null;
  created_at: string | null;
  completed_at: string | null;
  failure_reason: string | null;
}

export interface ReportCreateApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  report: ReportItem;
}

export interface ReportListApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  items: ReportItem[];
}

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

// ── Schedule types ──

export interface ReportSchedule {
  schedule_id: string;
  name: string;
  report_type: string;
  format: string;
  schedule_type: string;
  timezone_name: string;
  is_active: boolean;
  next_run_at: string | null;
  created_by: string;
  created_at: string | null;
  last_triggered_at: string | null;
}

export interface ReportScheduleCreateRequest {
  name: string;
  report_type: string;
  format: string;
  schedule_type: string;
  timezone_name: string;
  parameters: Record<string, unknown>;
  sensitivity_level: string | null;
  recipients: string[];
  local_time: string | null;
  once_at: string | null;
  day_of_week: number | null;
  day_of_month: number | null;
}

export interface ReportScheduleListResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  items: ReportSchedule[];
}

export interface ReportScheduleCreateResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: ReportSchedule;
  preview: string[];
}

export interface ReportScheduleDeleteResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  deleted: boolean;
}

export function reportScheduleFromApi(item: {
  schedule_id: string;
  name: string;
  report_type: string;
  format: string;
  schedule_type: string;
  timezone_name: string;
  is_active: boolean;
  next_run_at: string | null;
  created_by: string;
  created_at: string | null;
  last_triggered_at: string | null;
}): ReportSchedule {
  return {
    schedule_id: item.schedule_id,
    name: item.name,
    report_type: item.report_type,
    format: item.format,
    schedule_type: item.schedule_type,
    timezone_name: item.timezone_name,
    is_active: item.is_active,
    next_run_at: item.next_run_at,
    created_by: item.created_by,
    created_at: item.created_at,
    last_triggered_at: item.last_triggered_at,
  };
}

export const syntheticSchedules: ReportSchedule[] = [
  {
    schedule_id: "sched-daily-1",
    name: "Günlük Özet Raporu",
    report_type: "SUMMARY",
    format: "PDF",
    schedule_type: "DAILY",
    timezone_name: "Europe/Istanbul",
    is_active: true,
    next_run_at: "2026-07-25T08:00:00Z",
    created_by: "test-user",
    created_at: "2026-07-24T10:00:00Z",
    last_triggered_at: "2026-07-24T08:00:00Z",
  },
  {
    schedule_id: "sched-weekly-1",
    name: "Haftalık Detay Raporu",
    report_type: "DETAIL",
    format: "XLSX",
    schedule_type: "WEEKLY",
    timezone_name: "Europe/Istanbul",
    is_active: true,
    next_run_at: "2026-07-28T09:00:00Z",
    created_by: "test-user",
    created_at: "2026-07-20T10:00:00Z",
    last_triggered_at: "2026-07-21T09:00:00Z",
  },
  {
    schedule_id: "sched-monthly-1",
    name: "Aylık Kritik Veri Raporu",
    report_type: "CRITICAL_DATA",
    format: "PDF",
    schedule_type: "MONTHLY",
    timezone_name: "Europe/Istanbul",
    is_active: false,
    next_run_at: null,
    created_by: "test-user",
    created_at: "2026-07-01T10:00:00Z",
    last_triggered_at: "2026-07-01T08:00:00Z",
  },
];

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
