import type {
  ScoreComparisonApiResponse,
  ScoreDetailApiResponse,
  ScoreListApiResponse,
  ScoreTrendApiResponse,
  TrendGranularity,
} from "./model";
import { developmentFetch } from "../development/fetch";

export type ScoreErrorKind =
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "validation"
  | "technical";

export class ScoreApiError extends Error {
  constructor(
    public readonly kind: ScoreErrorKind,
    public readonly correlationId?: string,
  ) {
    super("Score request failed.");
  }
}

function classifyStatus(status: number): ScoreErrorKind {
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 404) return "not_found";
  if (status === 409) return "conflict";
  if (status === 400 || status === 422) return "validation";
  return "technical";
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new ScoreApiError(classifyStatus(response.status), correlationId);
  }
  return response.json() as Promise<T>;
}

export interface ScoreListParams {
  scopeType?: string;
  scopeId?: string;
  periodStart?: string;
  periodEnd?: string;
  scoreStatus?: string;
  limit?: number;
}

export async function fetchScores(
  params: ScoreListParams = {},
  signal?: AbortSignal,
): Promise<ScoreListApiResponse> {
  const searchParams = new URLSearchParams();
  if (params.scopeType) searchParams.set("scope_type", params.scopeType);
  if (params.scopeId) searchParams.set("scope_id", params.scopeId);
  if (params.periodStart) searchParams.set("period_start", params.periodStart);
  if (params.periodEnd) searchParams.set("period_end", params.periodEnd);
  if (params.scoreStatus) searchParams.set("score_status", params.scoreStatus);
  if (params.limit !== undefined) searchParams.set("limit", String(params.limit));
  const query = searchParams.toString();
  const url = `/api/v1/scores${query ? `?${query}` : ""}`;
  const response = await developmentFetch(url, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  return handleResponse<ScoreListApiResponse>(response);
}

export async function fetchScoreDetail(
  qualityScoreId: string,
  signal?: AbortSignal,
): Promise<ScoreDetailApiResponse> {
  const response = await developmentFetch(`/api/v1/scores/${qualityScoreId}`, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  return handleResponse<ScoreDetailApiResponse>(response);
}

export async function fetchScoreComparison(
  currentScoreId: string,
  previousScoreId: string,
  signal?: AbortSignal,
): Promise<ScoreComparisonApiResponse> {
  const searchParams = new URLSearchParams({
    current_score_id: currentScoreId,
    previous_score_id: previousScoreId,
  });
  const response = await developmentFetch(
    `/api/v1/scores/comparison?${searchParams.toString()}`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  return handleResponse<ScoreComparisonApiResponse>(response);
}

export interface ScoreTrendParams {
  scopeType: string;
  scopeId?: string;
  periodStart?: string;
  periodEnd?: string;
  granularity?: TrendGranularity;
}

export async function fetchScoreTrend(
  params: ScoreTrendParams,
  signal?: AbortSignal,
): Promise<ScoreTrendApiResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set("scope_type", params.scopeType);
  if (params.scopeId) searchParams.set("scope_id", params.scopeId);
  if (params.periodStart) searchParams.set("period_start", params.periodStart);
  if (params.periodEnd) searchParams.set("period_end", params.periodEnd);
  if (params.granularity) searchParams.set("granularity", params.granularity);
  const response = await developmentFetch(
    `/api/v1/scores/trend?${searchParams.toString()}`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  return handleResponse<ScoreTrendApiResponse>(response);
}

export async function fetchDatasetScores(
  datasetId: string,
  limit = 200,
  signal?: AbortSignal,
): Promise<ScoreListApiResponse> {
  const response = await developmentFetch(
    `/api/v1/datasets/${encodeURIComponent(datasetId)}/scores?limit=${limit}`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  return handleResponse<ScoreListApiResponse>(response);
}

export interface ScoreRuleHistoryApiResponse {
  api_version: string;
  data_origin: string;
  correlation_id: string;
  rule_version_id: string;
  items: ScoreListApiResponse["items"];
}

/**
 * @deprecated Kullanılmayan — UI'ya bağlanmadı. İlgili endpoint: GET /api/v1/rules/{id}/scores.
 * Bir skor karşılaştırma veya kural detay görünümüne entegre edilebilir; aksi halde kaldırılabilir.
 */
export async function fetchRuleScores(
  ruleId: string,
  signal?: AbortSignal,
): Promise<ScoreRuleHistoryApiResponse> {
  const response = await developmentFetch(
    `/api/v1/rules/${encodeURIComponent(ruleId)}/scores`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  return handleResponse<ScoreRuleHistoryApiResponse>(response);
}
