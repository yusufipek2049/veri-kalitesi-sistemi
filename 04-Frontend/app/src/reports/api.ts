import type {
  ReportCreateApiResponse,
  ReportListApiResponse,
  ReportRequest,
  ReportScheduleCreateRequest,
  ReportScheduleCreateResponse,
  ReportScheduleDeleteResponse,
  ReportScheduleListResponse,
  ReportSummaryApiResponse,
} from "./model";
import { developmentFetch } from "../development/fetch";

export class ReportApiError extends Error {
  constructor(
    public readonly kind: "unauthorized" | "technical",
    public readonly correlationId?: string,
  ) {
    super("Report request failed.");
  }
}

export async function fetchReportSummary(
  signal?: AbortSignal,
): Promise<ReportSummaryApiResponse> {
  const response = await developmentFetch("/api/v1/reports/summary", {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new ReportApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      correlationId,
    );
  }
  return response.json() as Promise<ReportSummaryApiResponse>;
}

export async function createReport(
  request: ReportRequest,
  signal?: AbortSignal,
): Promise<ReportCreateApiResponse> {
  const response = await developmentFetch("/api/v1/reports/", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
    signal,
  });
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new ReportApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      correlationId,
    );
  }
  return response.json() as Promise<ReportCreateApiResponse>;
}

export async function listReports(
  limit = 50,
  offset = 0,
  signal?: AbortSignal,
): Promise<ReportListApiResponse> {
  const response = await developmentFetch(
    `/api/v1/reports/?limit=${limit}&offset=${offset}`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new ReportApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      correlationId,
    );
  }
  return response.json() as Promise<ReportListApiResponse>;
}

export async function getReport(
  reportId: string,
  signal?: AbortSignal,
): Promise<ReportCreateApiResponse> {
  const response = await developmentFetch(`/api/v1/reports/${reportId}`, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new ReportApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      correlationId,
    );
  }
  return response.json() as Promise<ReportCreateApiResponse>;
}

export function downloadReportUrl(reportId: string): string {
  return `/api/v1/reports/${reportId}/download`;
}

export async function triggerDownload(
  reportId: string,
  filename: string,
): Promise<void> {
  const response = await developmentFetch(downloadReportUrl(reportId), {
    credentials: "same-origin",
  });
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new ReportApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      correlationId,
    );
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

// ── Schedule API ──

export async function fetchSchedules(
  signal?: AbortSignal,
): Promise<ReportScheduleListResponse> {
  const response = await developmentFetch("/api/v1/report-schedules", {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new ReportApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      correlationId,
    );
  }
  return response.json() as Promise<ReportScheduleListResponse>;
}

export async function createSchedule(
  request: ReportScheduleCreateRequest,
  signal?: AbortSignal,
): Promise<ReportScheduleCreateResponse> {
  const response = await developmentFetch("/api/v1/report-schedules", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
    signal,
  });
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new ReportApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      correlationId,
    );
  }
  return response.json() as Promise<ReportScheduleCreateResponse>;
}

export async function deleteSchedule(
  scheduleId: string,
  signal?: AbortSignal,
): Promise<ReportScheduleDeleteResponse> {
  const response = await developmentFetch(
    `/api/v1/report-schedules/${scheduleId}`,
    {
      method: "DELETE",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new ReportApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      correlationId,
    );
  }
  return response.json() as Promise<ReportScheduleDeleteResponse>;
}
