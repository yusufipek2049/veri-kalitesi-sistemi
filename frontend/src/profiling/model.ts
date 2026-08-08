export type ProfilingState = "normal" | "loading" | "empty" | "error" | "unauthorized" | "long-content";

export interface ProfileSnapshotListItem {
  profileId: string;
  datasetId: string;
  executionId: string;
  method: string;
  status: string;
  sampleRatio: number | null;
  durationMs: number;
  startedAt: string;
  finishedAt: string;
}

export interface ProfileSnapshotDetail {
  profileId: string;
  datasetId: string;
  executionId: string;
  method: string;
  status: string;
  sampleRatio: number | null;
  durationMs: number;
  metrics: Record<string, unknown>;
  startedAt: string;
  finishedAt: string;
}

export interface DriftSignal {
  kind: string;
  breached: boolean;
  result_kind: string;
  field?: string;
  baseline_value?: unknown;
  current_value?: unknown;
  threshold?: number;
  actual_value?: number;
}

export interface DriftJudgment {
  comparisonId: string;
  datasetId: string;
  baselineProfileId: string;
  currentProfileId: string;
  policyVersion: string | null;
  status: string;
  anomalyCandidate: boolean | null;
  result: {
    signals?: DriftSignal[];
    configuration_error?: string;
  };
  message: string;
  createdAt: string;
}

export interface ProfileSnapshotListApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  dataset_id: string;
  limit: number;
  items: Array<{
    profile_id: string;
    dataset_id: string;
    execution_id: string;
    method: string;
    status: string;
    sample_ratio: number | null;
    duration_ms: number;
    started_at: string;
    finished_at: string;
  }>;
}

export interface ProfileSnapshotDetailApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  profile_id: string;
  dataset_id: string;
  execution_id: string;
  method: string;
  status: string;
  sample_ratio: number | null;
  duration_ms: number;
  metrics: Record<string, unknown>;
  started_at: string;
  finished_at: string;
}

export interface DriftJudgmentApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: {
    comparison_id: string;
    dataset_id: string;
    baseline_profile_id: string;
    current_profile_id: string;
    policy_version: string | null;
    status: string;
    anomaly_candidate: boolean | null;
    result: {
      signals?: DriftSignal[];
      configuration_error?: string;
    };
    message: string;
    created_at: string;
  };
}

export function snapshotListItemFromApi(item: ProfileSnapshotListApiResponse["items"][0]): ProfileSnapshotListItem {
  return {
    profileId: item.profile_id,
    datasetId: item.dataset_id,
    executionId: item.execution_id,
    method: item.method,
    status: item.status,
    sampleRatio: item.sample_ratio,
    durationMs: item.duration_ms,
    startedAt: item.started_at,
    finishedAt: item.finished_at,
  };
}

export function snapshotDetailFromApi(response: ProfileSnapshotDetailApiResponse): ProfileSnapshotDetail {
  return {
    profileId: response.profile_id,
    datasetId: response.dataset_id,
    executionId: response.execution_id,
    method: response.method,
    status: response.status,
    sampleRatio: response.sample_ratio,
    durationMs: response.duration_ms,
    metrics: response.metrics,
    startedAt: response.started_at,
    finishedAt: response.finished_at,
  };
}

export function driftJudgmentFromApi(response: DriftJudgmentApiResponse): DriftJudgment {
  return {
    comparisonId: response.item.comparison_id,
    datasetId: response.item.dataset_id,
    baselineProfileId: response.item.baseline_profile_id,
    currentProfileId: response.item.current_profile_id,
    policyVersion: response.item.policy_version,
    status: response.item.status,
    anomalyCandidate: response.item.anomaly_candidate,
    result: response.item.result,
    message: response.item.message,
    createdAt: response.item.created_at,
  };
}

export const syntheticSnapshots: ProfileSnapshotListItem[] = [
  {
    profileId: "profile-001",
    datasetId: "ds-core-banking",
    executionId: "exec-001",
    method: "FULL",
    status: "COMPLETED",
    sampleRatio: 1.0,
    durationMs: 1250,
    startedAt: "2026-08-03T10:00:00Z",
    finishedAt: "2026-08-03T10:00:01Z",
  },
  {
    profileId: "profile-002",
    datasetId: "ds-core-banking",
    executionId: "exec-002",
    method: "FULL",
    status: "COMPLETED",
    sampleRatio: 1.0,
    durationMs: 1180,
    startedAt: "2026-08-02T10:00:00Z",
    finishedAt: "2026-08-02T10:00:01Z",
  },
];

export const syntheticSnapshotDetail: ProfileSnapshotDetail = {
  profileId: "profile-001",
  datasetId: "ds-core-banking",
  executionId: "exec-001",
  method: "FULL",
  status: "COMPLETED",
  sampleRatio: 1.0,
  durationMs: 1250,
  metrics: {
    row_count: 15000,
    profile_contract: {
      snapshot_version: "DQ_PROFILE_SNAPSHOT_V1",
      policy_version: "POLICY_V1",
      fingerprint: "abc123def456",
    },
  },
  startedAt: "2026-08-03T10:00:00Z",
  finishedAt: "2026-08-03T10:00:01Z",
};

export const syntheticDriftJudgment: DriftJudgment = {
  comparisonId: "comparison-001",
  datasetId: "ds-core-banking",
  baselineProfileId: "profile-002",
  currentProfileId: "profile-001",
  policyVersion: "POLICY_V1",
  status: "COMPLETED",
  anomalyCandidate: false,
  result: {
    signals: [
      {
        kind: "VOLUME_CHANGE",
        breached: false,
        result_kind: "NOMINAL",
        field: undefined,
        baseline_value: 14500,
        current_value: 15000,
        threshold: 0.1,
        actual_value: 0.034,
      },
    ],
  },
  message: "Drift analysis completed. No significant changes detected.",
  createdAt: "2026-08-03T10:05:00Z",
};
