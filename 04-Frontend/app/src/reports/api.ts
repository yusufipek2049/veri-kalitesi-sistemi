import type { ReportSummaryApiResponse } from "./model";

export class ReportApiError extends Error {
  constructor(
    public readonly kind: "unauthorized" | "technical",
    public readonly correlationId?: string,
  ) {
    super("Report summary request failed.");
  }
}

export async function fetchReportSummary(
  signal?: AbortSignal,
): Promise<ReportSummaryApiResponse> {
  const response = await fetch("/api/v1/reports/summary", {
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
