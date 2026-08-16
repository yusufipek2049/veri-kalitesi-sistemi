import type { MetricRatio } from "./api";

export type AnalyticsPageState = "normal" | "loading" | "empty" | "error" | "unauthorized";

export interface RuleHealthSummary {
  datasetCoverage: MetricRatio;
  fieldCoverage: MetricRatio;
  criticalCoverage: MetricRatio;
  activeRuleCount: number;
  neverExecutedCount: number;
  flakyRuleCount: number;
  technicalErrorRatio: MetricRatio;
  successRate: MetricRatio;
}

export interface MetadataHealthSummary {
  ownershipCompleteness: MetricRatio;
  classificationCompleteness: MetricRatio;
  sensitiveMarkingCompleteness: MetricRatio;
  policyCurrency: MetricRatio;
  staleDatasetCount: number;
  staleFieldCount: number;
  criticalGapCount: number;
  staleAfterDays: number;
}

export interface IssuePerformanceSummary {
  openIssueCount: number;
  criticalOpenCount: number;
  mttaP50: number | null;
  mttaP95: number | null;
  mttaSampleCount: number;
  mttrP50: number | null;
  mttrP95: number | null;
  mttrSampleCount: number;
  unresolvedCount: number;
  verificationSuccessRate: MetricRatio;
  recurringIssueCount: number;
  reopenedCount: number;
  agingIssueCount: number;
  missingTimelineCount: number;
}

export interface ScoringPolicyImpactSummary {
  activeVersion: string | null;
  baselineVersion: string;
  candidateVersion: string;
  observedAverageDelta: number | null;
  simulatedAverageDelta: number | null;
  improvedCount: number;
  deterioratedCount: number;
  unchangedCount: number;
  levelChangedCount: number;
  notSimulatableCount: number;
}

// ── Mapping helpers ──

function toMetricRatio(raw: unknown): MetricRatio {
  if (!raw || typeof raw !== "object") return { numerator: 0, denominator: 0, ratio: null, reason_code: "NO_DATA" };
  const r = raw as Record<string, unknown>;
  return {
    numerator: (r.numerator as number) ?? 0,
    denominator: (r.denominator as number) ?? 0,
    ratio: (r.ratio as number | null) ?? null,
    reason_code: (r.reason_code as string | null) ?? null,
  };
}

export function ruleHealthSummaryFromApi(summary: Record<string, unknown>): RuleHealthSummary {
  return {
    datasetCoverage: toMetricRatio(summary.dataset_coverage),
    fieldCoverage: toMetricRatio(summary.field_coverage),
    criticalCoverage: toMetricRatio(summary.critical_coverage),
    activeRuleCount: (summary.active_rule_count as number) ?? 0,
    neverExecutedCount: (summary.never_executed_count as number) ?? 0,
    flakyRuleCount: (summary.flaky_rule_count as number) ?? 0,
    technicalErrorRatio: toMetricRatio(summary.technical_error_ratio),
    successRate: toMetricRatio(summary.success_rate),
  };
}

export function metadataHealthSummaryFromApi(summary: Record<string, unknown>): MetadataHealthSummary {
  return {
    ownershipCompleteness: toMetricRatio(summary.ownership_completeness),
    classificationCompleteness: toMetricRatio(summary.classification_completeness),
    sensitiveMarkingCompleteness: toMetricRatio(summary.sensitive_marking_completeness),
    policyCurrency: toMetricRatio(summary.policy_currency),
    staleDatasetCount: (summary.stale_dataset_count as number) ?? 0,
    staleFieldCount: (summary.stale_field_count as number) ?? 0,
    criticalGapCount: (summary.critical_gap_count as number) ?? 0,
    staleAfterDays: (summary.stale_after_days as number) ?? 30,
  };
}

export function issuePerformanceSummaryFromApi(summary: Record<string, unknown>): IssuePerformanceSummary {
  return {
    openIssueCount: (summary.open_issue_count as number) ?? 0,
    criticalOpenCount: (summary.critical_open_count as number) ?? 0,
    mttaP50: (summary.mtta_p50 as number | null) ?? null,
    mttaP95: (summary.mtta_p95 as number | null) ?? null,
    mttaSampleCount: (summary.mtta_sample_count as number) ?? 0,
    mttrP50: (summary.mttr_p50 as number | null) ?? null,
    mttrP95: (summary.mttr_p95 as number | null) ?? null,
    mttrSampleCount: (summary.mttr_sample_count as number) ?? 0,
    unresolvedCount: (summary.unresolved_count as number) ?? 0,
    verificationSuccessRate: toMetricRatio(summary.verification_success_rate),
    recurringIssueCount: (summary.recurring_issue_count as number) ?? 0,
    reopenedCount: (summary.reopened_count as number) ?? 0,
    agingIssueCount: (summary.aging_issue_count as number) ?? 0,
    missingTimelineCount: (summary.missing_timeline_count as number) ?? 0,
  };
}

export function scoringPolicyImpactSummaryFromApi(summary: Record<string, unknown>): ScoringPolicyImpactSummary {
  return {
    activeVersion: (summary.active_version as string | null) ?? null,
    baselineVersion: (summary.baseline_version as string) ?? "",
    candidateVersion: (summary.candidate_version as string) ?? "",
    observedAverageDelta: (summary.observed_average_delta as number | null) ?? null,
    simulatedAverageDelta: (summary.simulated_average_delta as number | null) ?? null,
    improvedCount: (summary.improved_count as number) ?? 0,
    deterioratedCount: (summary.deteriorated_count as number) ?? 0,
    unchangedCount: (summary.unchanged_count as number) ?? 0,
    levelChangedCount: (summary.level_changed_count as number) ?? 0,
    notSimulatableCount: (summary.not_simulatable_count as number) ?? 0,
  };
}

// ── Duration formatting ──

export function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${(seconds / 86400).toFixed(1)}d`;
}

export function formatRatio(ratio: MetricRatio): string {
  if (ratio.ratio === null) return "—";
  return `${(ratio.ratio * 100).toFixed(1)}%`;
}

export function ratioTooltip(ratio: MetricRatio): string {
  return `${ratio.numerator} / ${ratio.denominator}`;
}
