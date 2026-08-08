import type { DashboardFilters, DashboardSummaryApiResponse } from "./model";
import { filtersToSearchParams } from "./model";
import { developmentFetch } from "../development/fetch";

export type DashboardApiErrorKind = "unauthorized" | "scope-forbidden" | "invalid-filter" | "technical" | "invalid-response";

export class DashboardApiError extends Error {
  constructor(
    public readonly kind: DashboardApiErrorKind,
    public readonly correlationId: string,
  ) {
    super("Dashboard API request failed.");
  }
}

export async function fetchDashboardSummary(
  filters?: DashboardFilters,
  signal?: AbortSignal,
): Promise<DashboardSummaryApiResponse> {
  const queryString = filters ? filtersToSearchParams(filters).toString() : "";
  const url = queryString ? `/api/v1/dashboard/summary?${queryString}` : "/api/v1/dashboard/summary";
  const response = await developmentFetch(url, {
    credentials: "include",
    headers: { Accept: "application/json" },
    method: "GET",
    signal,
  });
  const correlationId = response.headers.get("X-Correlation-ID") ?? "izleme-kodu-yok";
  if (response.status === 401) {
    throw new DashboardApiError("unauthorized", correlationId);
  }
  if (response.status === 403) {
    throw new DashboardApiError("scope-forbidden", correlationId);
  }
  if (response.status === 400) {
    throw new DashboardApiError("invalid-filter", correlationId);
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
    && ["EXECUTIVE", "ENGINEER"].includes(candidate.role_view ?? "")
    && Array.isArray(candidate.periods)
    && candidate.periods.every((period) => (
      typeof period?.period_start === "string"
      && typeof period?.period_end === "string"
      && Array.isArray(period?.observations)
      && period.observations.every(isDashboardObservation)
    ))
    && isOperationalIndicators(candidate.operational_indicators)
    && (candidate.applied_filters === null || isAppliedFilters(candidate.applied_filters));
}

function isAppliedFilters(value: unknown): boolean {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  return typeof candidate.window_start === "string"
    && typeof candidate.window_end === "string"
    && (candidate.scope_type === null || typeof candidate.scope_type === "string")
    && (candidate.scope_id === null || typeof candidate.scope_id === "string")
    && (candidate.score_status === null || typeof candidate.score_status === "string")
    && (candidate.level === null || typeof candidate.level === "string");
}

function isDashboardObservation(
  value: DashboardSummaryApiResponse["periods"][number]["observations"][number],
): boolean {
  return Boolean(
    value
      && typeof value.quality_score_id === "string"
      && ["ENTERPRISE", "SOURCE"].includes(value.scope_type)
      && (value.scope_id === null || typeof value.scope_id === "string")
      && typeof value.score_status === "string"
      && typeof value.calculated_at === "string"
      && ["COMPARABLE", "NOT_COMPARABLE", "UNKNOWN"].includes(value.comparison_status)
      && Array.isArray(value.comparison_reason_codes)
      && value.comparison_reason_codes.every((reason) => typeof reason === "string")
      && (value.change === null || typeof value.change === "string" || typeof value.change === "number")
      && (value.contribution_graph === null || typeof value.contribution_graph === "object")
      && (value.trend === null || typeof value.trend === "object"),
  );
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
