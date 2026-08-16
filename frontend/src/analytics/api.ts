import { developmentFetch } from "../development/fetch";

export type AnalyticsErrorKind = "unauthorized" | "forbidden" | "not_found" | "validation" | "technical";

export class AnalyticsApiError extends Error {
  constructor(
    public readonly kind: AnalyticsErrorKind,
    public readonly correlationId?: string,
  ) {
    super("Analytics request failed.");
  }
}

export interface AnalyticsFilterParams {
  startDate?: string;
  endDate?: string;
  sourceId?: string;
  datasetId?: string;
}

function classifyStatus(status: number): AnalyticsErrorKind {
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 404) return "not_found";
  if (status === 400 || status === 422) return "validation";
  return "technical";
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new AnalyticsApiError(classifyStatus(response.status), correlationId);
  }
  return response.json() as Promise<T>;
}

function buildQuery(params: AnalyticsFilterParams, extra?: Record<string, string | undefined>): string {
  const searchParams = new URLSearchParams();
  if (params.startDate) searchParams.set("start_date", params.startDate);
  if (params.endDate) searchParams.set("end_date", params.endDate);
  if (params.sourceId) searchParams.set("source_id", params.sourceId);
  if (params.datasetId) searchParams.set("dataset_id", params.datasetId);
  if (extra) {
    for (const [key, value] of Object.entries(extra)) {
      if (value) searchParams.set(key, value);
    }
  }
  const q = searchParams.toString();
  return q ? `?${q}` : "";
}

export interface MetricRatio {
  numerator: number;
  denominator: number;
  ratio: number | null;
  reason_code: string | null;
}

export interface AnalyticsEnvelope {
  api_version: string;
  data_origin: string;
  correlation_id: string;
  as_of: string;
  applied_filters: Record<string, string | null>;
  summary: Record<string, unknown>;
  breakdowns: Record<string, unknown>;
  items: Record<string, unknown>[];
}

export async function fetchRuleHealth(
  params: AnalyticsFilterParams = {},
  extra?: { dimension?: string; criticality?: string; ruleStatus?: string },
  signal?: AbortSignal,
): Promise<AnalyticsEnvelope> {
  const query = buildQuery(params, {
    dimension: extra?.dimension,
    criticality: extra?.criticality,
    rule_status: extra?.ruleStatus,
  });
  const response = await developmentFetch(`/api/v1/dashboard/rule-health${query}`, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  return handleResponse<AnalyticsEnvelope>(response);
}

export async function fetchMetadataHealth(
  params: AnalyticsFilterParams = {},
  extra?: { classification?: string; criticality?: string; ownershipStatus?: string },
  signal?: AbortSignal,
): Promise<AnalyticsEnvelope> {
  const query = buildQuery(params, {
    classification: extra?.classification,
    criticality: extra?.criticality,
    ownership_status: extra?.ownershipStatus,
  });
  const response = await developmentFetch(`/api/v1/dashboard/metadata-health${query}`, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  return handleResponse<AnalyticsEnvelope>(response);
}

export async function fetchIssuePerformance(
  params: AnalyticsFilterParams = {},
  extra?: { priority?: string; status?: string; triggerType?: string },
  signal?: AbortSignal,
): Promise<AnalyticsEnvelope> {
  const query = buildQuery(params, {
    priority: extra?.priority,
    status: extra?.status,
    trigger_type: extra?.triggerType,
  });
  const response = await developmentFetch(`/api/v1/dashboard/issue-performance${query}`, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  return handleResponse<AnalyticsEnvelope>(response);
}

export async function fetchScoringPolicyImpact(
  params: AnalyticsFilterParams = {},
  extra?: { baselineVersion?: string; candidateVersion?: string },
  signal?: AbortSignal,
): Promise<AnalyticsEnvelope> {
  const query = buildQuery(params, {
    baseline_version: extra?.baselineVersion,
    candidate_version: extra?.candidateVersion,
  });
  const response = await developmentFetch(`/api/v1/dashboard/scoring-policy-impact${query}`, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  return handleResponse<AnalyticsEnvelope>(response);
}
