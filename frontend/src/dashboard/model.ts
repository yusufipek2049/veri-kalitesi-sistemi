export type DashboardState = "normal" | "loading" | "empty" | "error" | "unauthorized";

export type ScoreStatus = "CALCULATED" | "NOT_CALCULATED" | "NO_DATA" | "PARTIAL" | "NOT_CALCULATED_TECHNICAL_ERROR" | "CONFIG_ERROR";
export type ScoreLevel = "GOOD" | "ACCEPTABLE" | "RISKY" | "CRITICAL";
export type ComparisonStatus = "COMPARABLE" | "NOT_COMPARABLE" | "UNKNOWN";

export interface DashboardScoreNode {
  qualityScoreId: string;
  scopeType: string;
  scopeId: string | null;
  scoreValue: number | null;
  scoreStatus: ScoreStatus;
  level: ScoreLevel | null;
  calculatedAt: string;
  comparisonStatus: ComparisonStatus;
  comparisonReasonCodes: string[];
  change: number | null;
  trend?: {
    movingAverage: number | null;
    consecutiveDeteriorationCount: number | null;
    suddenDeterioration: boolean | null;
    timeBelowThresholdPeriods: number | null;
    improvementPersistence: number | null;
  };
  versionBoundary: boolean;
  policyVersion: string | null;
}

export interface DashboardTrendPeriod {
  periodStart: string;
  periodEnd: string;
  observations: DashboardScoreNode[];
}

export interface DashboardTrend {
  asOf: string;
  periods: DashboardTrendPeriod[];
  hasData: boolean;
  thresholdValue: number | null;
}

export interface AppliedDashboardFilters {
  windowStart: string;
  windowEnd: string;
  scopeType: string | null;
  scopeId: string | null;
  scoreStatus: string | null;
  level: string | null;
}

export interface MeasurementQualification {
  status: "NO_DATA" | "VALIDATION_REQUIRED" | "TECHNICAL_FAILURE";
  evaluatedScopeCount: number;
  reasonCodes: string[];
}

export interface TechnicalErrors {
  observationCount: number;
  executionCount: number;
  affectedSourceCount: number;
  lastOccurredAt: string | null;
}

export interface OperationalIndicators {
  measurementQualification: MeasurementQualification;
  technicalErrors: TechnicalErrors;
}

export interface DashboardOverview {
  trend: DashboardTrend;
  operationalIndicators: OperationalIndicators;
  roleView: string;
  appliedFilters: AppliedDashboardFilters | null;
}

// ── API response shape ──

interface ApiScoreNode {
  quality_score_id: string;
  scope_type: string;
  scope_id: string | null;
  score_value: number | null;
  score_status: string;
  level: string | null;
  calculated_at: string;
  comparison_status: string;
  comparison_reason_codes: string[];
  change: number | null;
  trend?: ApiScoreTrend;
  version_boundary?: boolean;
  policy_version?: string | null;
}

interface ApiTrendPeriod {
  period_start: string;
  period_end: string;
  observations: ApiScoreNode[];
}

interface ApiScoreTrend {
  moving_average: number | null;
  consecutive_deterioration_count: number | null;
  sudden_deterioration: boolean | null;
  time_below_threshold_periods: number | null;
  improvement_persistence: number | null;
}

interface ApiTrend {
  as_of: string;
  periods: ApiTrendPeriod[];
  has_data: boolean;
  threshold_value?: number | null;
}

interface ApiAppliedDashboardFilters {
  window_start: string;
  window_end: string;
  scope_type: string | null;
  scope_id: string | null;
  score_status: string | null;
  level: string | null;
}

interface ApiMeasurementQualification {
  status: string;
  evaluated_scope_count: number;
  reason_codes: string[];
}

interface ApiTechnicalErrors {
  observation_count: number;
  execution_count: number;
  affected_source_count: number;
  last_occurred_at: string | null;
}

interface ApiOperationalIndicators {
  measurement_qualification: ApiMeasurementQualification;
  technical_errors: ApiTechnicalErrors;
}

export interface DashboardOverviewApiResponse {
  api_version: string;
  data_origin: string;
  correlation_id: string;
  trend: ApiTrend;
  operational_indicators: ApiOperationalIndicators;
  role_view: string;
  applied_filters?: ApiAppliedDashboardFilters | null;
}

// ── Mapping helpers ──

function mapNode(raw: ApiScoreNode): DashboardScoreNode {
  return {
    qualityScoreId: raw.quality_score_id,
    scopeType: raw.scope_type,
    scopeId: raw.scope_id,
    scoreValue: raw.score_value,
    scoreStatus: raw.score_status as ScoreStatus,
    level: (raw.level as ScoreLevel | null) ?? null,
    calculatedAt: raw.calculated_at,
    comparisonStatus: (raw.comparison_status as ComparisonStatus) || "UNKNOWN",
    comparisonReasonCodes: raw.comparison_reason_codes ?? [],
    change: raw.change,
    trend: raw.trend
      ? {
          movingAverage: raw.trend.moving_average,
          consecutiveDeteriorationCount: raw.trend.consecutive_deterioration_count,
          suddenDeterioration: raw.trend.sudden_deterioration,
          timeBelowThresholdPeriods: raw.trend.time_below_threshold_periods,
          improvementPersistence: raw.trend.improvement_persistence,
        }
      : undefined,
    versionBoundary: raw.version_boundary ?? false,
    policyVersion: raw.policy_version ?? null,
  };
}

export function overviewFromApi(response: DashboardOverviewApiResponse): DashboardOverview {
  return {
    trend: {
      asOf: response.trend.as_of,
      periods: response.trend.periods.map((p) => ({
        periodStart: p.period_start,
        periodEnd: p.period_end,
        observations: p.observations.map(mapNode),
      })),
      hasData: response.trend.has_data,
      thresholdValue: response.trend.threshold_value ?? null,
    },
    operationalIndicators: {
      measurementQualification: {
        status: response.operational_indicators.measurement_qualification.status as MeasurementQualification["status"],
        evaluatedScopeCount: response.operational_indicators.measurement_qualification.evaluated_scope_count,
        reasonCodes: response.operational_indicators.measurement_qualification.reason_codes,
      },
      technicalErrors: {
        observationCount: response.operational_indicators.technical_errors.observation_count,
        executionCount: response.operational_indicators.technical_errors.execution_count,
        affectedSourceCount: response.operational_indicators.technical_errors.affected_source_count,
        lastOccurredAt: response.operational_indicators.technical_errors.last_occurred_at,
      },
    },
    roleView: response.role_view,
    appliedFilters: response.applied_filters
      ? {
          windowStart: response.applied_filters.window_start,
          windowEnd: response.applied_filters.window_end,
          scopeType: response.applied_filters.scope_type,
          scopeId: response.applied_filters.scope_id,
          scoreStatus: response.applied_filters.score_status,
          level: response.applied_filters.level,
        }
      : null,
  };
}
