export type ScoreState = "normal" | "loading" | "empty" | "error" | "unauthorized";

type ScoreScopeType = "RULE" | "DATASET" | "DIMENSION" | "SOURCE" | "ENTERPRISE";
type ScoreStatus = "CALCULATED" | "NOT_CALCULATED" | "NO_DATA" | "PARTIAL" | "NOT_CALCULATED_TECHNICAL_ERROR" | "CONFIG_ERROR";
type ScoreLevel = "GOOD" | "ACCEPTABLE" | "RISKY" | "CRITICAL";
type ComparisonStatus = "COMPARABLE" | "NOT_COMPARABLE" | "UNKNOWN";

export interface ScoreListItem {
  id: string;
  executionId: string;
  scopeType: ScoreScopeType;
  scopeId: string | null;
  scopeDisplayName: string | null;
  scopeParentName: string | null;
  scoreValue: number | null;
  scoreStatus: ScoreStatus;
  measurementStatus: string | null;
  level: ScoreLevel | null;
  policyVersion: string | null;
  calculatedAt: string;
  publicationId: string | null;
}

interface ScorePublicationSummary {
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
  calculationDetails: Record<string, unknown> | null;
  contributionGraph: ContributionGraphData | null;
}

export interface ContributionGraphComponent {
  component_ref: string;
  component_type: "RULE" | "DATASET" | "DIMENSION" | "SOURCE" | "UNKNOWN";
  component_name?: string | null;
  included: boolean;
  weight: string | null;
  contribution: string | null;
  exclusion_reason: string | null;
  score?: string | null;
  quality_score_id?: string | null;
  rule_version_id?: string | null;
  dataset_id?: string | null;
  data_source_id?: string | null;
  dimension?: string | null;
}

export interface ContributionGraphData {
  graph_version: string;
  quality_score_id: string;
  execution_id: string;
  scope: { type: string; id: string | null };
  official: boolean;
  raw_quality_score: string | null;
  technical_status: string;
  measurement_qualification: string;
  critical_rule_status: string;
  critical_veto: boolean | null;
  critical_asset_status: string;
  risk_status: string;
  sla_status: string;
  usage_decision: string;
  coverage_status: string;
  canonical_counts: Record<string, number | null> | null;
  evidence_references: string[];
  diagnosis_status: string;
  diagnosis_evidence_ref: string | null;
  versions: {
    rule_version: string | null;
    score_model_version: string | null;
    policy_version: string | null;
    threshold_version: string | null;
    qualification_policy_version: string | null;
    profile_version: string | null;
    governance_version: string | null;
  };
  components: ContributionGraphComponent[];
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
    scope_display_name: string | null;
    scope_parent_name: string | null;
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
  calculation_details: Record<string, unknown> | null;
  contribution_graph: ContributionGraphData | null;
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
    scopeDisplayName: raw.scope_display_name ?? null,
    scopeParentName: raw.scope_parent_name ?? null,
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
    calculationDetails: response.calculation_details ?? null,
    contributionGraph: response.contribution_graph ?? null,
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

// ── Score Trend ──

export type TrendGranularity = "day" | "week" | "month";

export interface ScoreTrendPoint {
  timestamp: string;
  scoreValue: number | null;
  level: ScoreLevel | null;
  change: number | null;
  scoreCount: number;
}

export interface ScoreTrendData {
  scopeType: string;
  scopeId: string | null;
  granularity: TrendGranularity;
  points: ScoreTrendPoint[];
}

export interface ScoreTrendApiResponse {
  api_version: string;
  data_origin: string;
  correlation_id: string;
  scope_type: string;
  scope_id: string | null;
  granularity: string;
  items: Array<{
    timestamp: string;
    score_value: number | null;
    level: string | null;
    change: number | null;
    score_count: number;
  }>;
}

export function trendFromApi(response: ScoreTrendApiResponse): ScoreTrendData {
  return {
    scopeType: response.scope_type,
    scopeId: response.scope_id,
    granularity: response.granularity as TrendGranularity,
    points: response.items.map((item) => ({
      timestamp: item.timestamp,
      scoreValue: item.score_value,
      level: (item.level as ScoreLevel | null) ?? null,
      change: item.change,
      scoreCount: item.score_count,
    })),
  };
}
