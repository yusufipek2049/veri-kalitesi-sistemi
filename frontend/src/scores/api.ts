import type {
  ScoreComparisonApiResponse,
  ScoreDetailApiResponse,
  ScoreListApiResponse,
  ScoreRuleHistoryApiResponse,
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

export async function fetchRuleScoreHistory(
  ruleVersionId: string,
  signal?: AbortSignal,
): Promise<ScoreRuleHistoryApiResponse> {
  const response = await developmentFetch(`/api/v1/scores/rules/${ruleVersionId}`, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  return handleResponse<ScoreRuleHistoryApiResponse>(response);
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
