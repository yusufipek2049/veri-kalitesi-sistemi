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
    ))
    && isOperationalIndicators(candidate.operational_indicators);
}

function isOperationalIndicators(
  value: DashboardSummaryApiResponse["operational_indicators"] | undefined,
): value is DashboardSummaryApiResponse["operational_indicators"] {
  if (!value || typeof value !== "object") return false;
  const qualification = value.measurement_qualification;
  const controls = value.critical_controls;
  const technical = value.technical_errors;
  return Boolean(
    qualification
      && ["NO_DATA", "VALIDATION_REQUIRED", "TECHNICAL_FAILURE"].includes(qualification.status)
      && isNonNegativeInteger(qualification.evaluated_scope_count)
      && Array.isArray(qualification.reason_codes)
      && qualification.reason_codes.every((reason) => typeof reason === "string")
      && (qualification.policy_version === null || typeof qualification.policy_version === "string")
      && controls
      && controls.status === "NOT_AVAILABLE"
      && typeof controls.reason_code === "string"
      && isNullableNonNegativeInteger(controls.passed_count)
      && isNullableNonNegativeInteger(controls.failed_count)
      && isNullableNonNegativeInteger(controls.not_evaluated_count)
      && technical
      && isNonNegativeInteger(technical.observation_count)
      && isNonNegativeInteger(technical.execution_count)
      && isNonNegativeInteger(technical.affected_source_count)
      && (technical.last_occurred_at === null || typeof technical.last_occurred_at === "string"),
  );
}

function isNonNegativeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

function isNullableNonNegativeInteger(value: unknown): value is number | null {
  return value === null || isNonNegativeInteger(value);
}
