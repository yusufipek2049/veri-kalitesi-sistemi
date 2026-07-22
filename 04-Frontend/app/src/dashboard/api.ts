import type { DashboardSummaryApiResponse } from "./model";

export type DashboardApiErrorKind = "unauthorized" | "technical" | "invalid-response";

export class DashboardApiError extends Error {
  constructor(
    public readonly kind: DashboardApiErrorKind,
    public readonly correlationId: string,
  ) {
    super("Dashboard API request failed.");
  }
}

export async function fetchDashboardSummary(signal?: AbortSignal): Promise<DashboardSummaryApiResponse> {
  const response = await fetch("/api/v1/dashboard/summary", {
    credentials: "include",
    headers: { Accept: "application/json" },
    method: "GET",
    signal,
  });
  const correlationId = response.headers.get("X-Correlation-ID") ?? "izleme-kodu-yok";
  if (response.status === 401 || response.status === 403) {
    throw new DashboardApiError("unauthorized", correlationId);
  }
  if (!response.ok) {
    throw new DashboardApiError("technical", correlationId);
  }
  const payload: unknown = await response.json();
  if (!isDashboardSummary(payload)) {
    throw new DashboardApiError("invalid-response", correlationId);
  }
  return payload;
}

function isDashboardSummary(payload: unknown): payload is DashboardSummaryApiResponse {
  if (!payload || typeof payload !== "object") return false;
  const candidate = payload as Partial<DashboardSummaryApiResponse>;
  return candidate.api_version === "v1"
    && typeof candidate.data_origin === "string"
    && typeof candidate.correlation_id === "string"
    && typeof candidate.as_of === "string"
    && typeof candidate.has_data === "boolean"
    && Array.isArray(candidate.periods)
    && candidate.periods.every((period) => (
      typeof period?.period_start === "string"
      && typeof period?.period_end === "string"
      && Array.isArray(period?.observations)
    ));
}
