export type ScoreState = "normal" | "loading" | "empty" | "error" | "unauthorized";

export type ScoreScopeType = "RULE" | "DATASET" | "DIMENSION" | "SOURCE" | "ENTERPRISE";
export type ScoreStatus = "CALCULATED" | "NOT_CALCULATED" | "NO_DATA" | "PARTIAL" | "NOT_CALCULATED_TECHNICAL_ERROR" | "CONFIG_ERROR";
export type ScoreLevel = "GOOD" | "ACCEPTABLE" | "RISKY" | "CRITICAL";
export type ComparisonStatus = "COMPARABLE" | "NOT_COMPARABLE" | "UNKNOWN";

export interface ScoreListItem {
  id: string;
  executionId: string;
  scopeType: ScoreScopeType;
  scopeId: string | null;
  scoreValue: number | null;
  scoreStatus: ScoreStatus;
  measurementStatus: string | null;
  level: ScoreLevel | null;
  policyVersion: string | null;
  calculatedAt: string;
  publicationId: string | null;
}

export interface ScorePublicationSummary {
  publicationId: string;
  executionId: string;
  period: string;
  status: "PUBLISHED" | "SUPERSEDED";
  policyVersion: string;
  publishedAt: string;
  supersededAt: string | null;
}

export interface ScoreDetail {
  item: ScoreListItem;
  publication: ScorePublicationSummary | null;
  availableActions: string[];
  hasContributionGraph: boolean;
}

export interface ScoreComparisonResult {
  currentScoreId: string;
  previousScoreId: string;
  comparisonStatus: ComparisonStatus;
  reasonCodes: string[];
  deltaValue: number | null;
}

// ── API response shapes ──

export interface ScoreListApiResponse {
  data_origin: string;
  correlation_id: string;
  items: Array<{
    quality_score_id: string;
    execution_id: string;
    scope_type: string;
    scope_id: string | null;
    score_value: string | null;
    score_status: string;
    measurement_status: string | null;
    level: string | null;
    policy_version: string | null;
    calculated_at: string;
    publication_id: string | null;
  }>;
}

export interface ScoreDetailApiResponse {
  data_origin: string;
  correlation_id: string;
  score: ScoreListApiResponse["items"][number];
  publication: {
    publication_id: string;
    execution_id: string;
    period: string;
    status: string;
    policy_version: string;
    published_at: string;
    superseded_at: string | null;
  } | null;
  available_actions: string[];
  has_contribution_graph: boolean;
}

export interface ScoreRuleHistoryApiResponse {
  data_origin: string;
  correlation_id: string;
  rule_version_id: string;
  items: ScoreListApiResponse["items"];
}

export interface ScoreComparisonApiResponse {
  data_origin: string;
  correlation_id: string;
  current_score_id: string;
  previous_score_id: string;
  comparison_status: string;
  reason_codes: string[];
  delta_value: string | null;
}

// ── Mapping helpers ──

function parseDecimal(value: string | null): number | null {
  if (value === null) return null;
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function mapScoreItem(raw: ScoreListApiResponse["items"][number]): ScoreListItem {
  return {
    id: raw.quality_score_id,
    executionId: raw.execution_id,
    scopeType: raw.scope_type as ScoreScopeType,
    scopeId: raw.scope_id,
    scoreValue: parseDecimal(raw.score_value),
    scoreStatus: raw.score_status as ScoreStatus,
    measurementStatus: raw.measurement_status,
    level: (raw.level as ScoreLevel | null) ?? null,
    policyVersion: raw.policy_version,
    calculatedAt: raw.calculated_at,
    publicationId: raw.publication_id,
  };
}

export function scoresFromApi(response: ScoreListApiResponse): ScoreListItem[] {
  return response.items.map(mapScoreItem);
}

export function scoreDetailFromApi(response: ScoreDetailApiResponse): ScoreDetail {
  return {
    item: mapScoreItem(response.score),
    publication: response.publication
      ? {
          publicationId: response.publication.publication_id,
          executionId: response.publication.execution_id,
          period: response.publication.period,
          status: response.publication.status as "PUBLISHED" | "SUPERSEDED",
          policyVersion: response.publication.policy_version,
          publishedAt: response.publication.published_at,
          supersededAt: response.publication.superseded_at,
        }
      : null,
    availableActions: response.available_actions ?? [],
    hasContributionGraph: response.has_contribution_graph,
  };
}

export function comparisonFromApi(response: ScoreComparisonApiResponse): ScoreComparisonResult {
  return {
    currentScoreId: response.current_score_id,
    previousScoreId: response.previous_score_id,
    comparisonStatus: response.comparison_status as ComparisonStatus,
    reasonCodes: response.reason_codes ?? [],
    deltaValue: parseDecimal(response.delta_value),
  };
}
