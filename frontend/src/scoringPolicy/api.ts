import { developmentFetch } from "../development/fetch";

export type ScoringPolicyErrorKind = "unauthorized" | "validation" | "technical";

export class ScoringPolicyApiError extends Error {
  constructor(
    public readonly kind: ScoringPolicyErrorKind,
    public readonly correlationId?: string,
  ) {
    super(
      kind === "unauthorized"
        ? correlationId
          ? `Skorlama politikası için yetkiniz yok. İzleme kodu: ${correlationId}.`
          : "Skorlama politikası için yetkiniz yok."
        : correlationId
          ? `Skorlama politikası işlemi tamamlanamadı. Yeniden deneyin. İzleme kodu: ${correlationId}.`
          : "Skorlama politikası işlemi tamamlanamadı. Yeniden deneyin.",
    );
  }
}

function scoringPolicyApiError(response: Response): ScoringPolicyApiError {
  const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
  const kind =
    response.status === 401 || response.status === 403
      ? "unauthorized"
      : response.status === 400 || response.status === 409 || response.status === 422
        ? "validation"
        : "technical";
  return new ScoringPolicyApiError(kind, correlationId);
}

export interface ScoringThresholdSetApi {
  version: string;
  critical_upper_exclusive: string;
  risky_upper_exclusive: string;
  acceptable_upper_exclusive: string;
}

export interface ScoringConfigurationApi {
  configuration_id: string;
  version: string;
  is_active: boolean;
  activated_at: string | null;
  created_by: string;
  created_at: string;
  threshold_set: ScoringThresholdSetApi;
  dimension_weights: Record<string, string>;
  criticality_weights: Record<string, string>;
  dataset_id: string | null;
}

export interface ScoringConfigurationApprovalApi {
  approval_id: string;
  configuration_id: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  maker_actor_id: string;
  checker_actor_id: string | null;
  policy_version: string;
  decision_reason_code: string | null;
  requested_at: string;
  decided_at: string | null;
}

export interface ScoringConfigurationEntryApi {
  configuration: ScoringConfigurationApi;
  approval: ScoringConfigurationApprovalApi | null;
}

export interface ScoringConfigurationListApiResponse {
  api_version: string;
  data_origin: string;
  correlation_id: string;
  active_configuration_id: string | null;
  pending_approval: ScoringConfigurationApprovalApi | null;
  items: ScoringConfigurationEntryApi[];
}

export interface ScoringConfigurationDetailApiResponse {
  api_version: string;
  data_origin: string;
  correlation_id: string;
  configuration: ScoringConfigurationApi;
  approval: ScoringConfigurationApprovalApi;
}

export async function fetchScoringConfigurations(
  signal?: AbortSignal,
  datasetId?: string,
): Promise<ScoringConfigurationListApiResponse> {
  const url = new URL("/api/v1/scoring-configurations", window.location.origin);
  if (datasetId) url.searchParams.set("dataset_id", datasetId);
  const response = await developmentFetch(url.toString(), {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw scoringPolicyApiError(response);
  }
  return response.json() as Promise<ScoringConfigurationListApiResponse>;
}

export interface ScoringConfigurationSubmitPayload {
  version: string;
  threshold_version?: string;
  critical_upper_exclusive?: string;
  risky_upper_exclusive?: string;
  acceptable_upper_exclusive?: string;
  dimension_weights?: Record<string, string>;
  criticality_weights?: Record<string, string>;
  dataset_id?: string | null;
}

async function postScoringPolicy(
  path: string,
  body: object,
): Promise<ScoringConfigurationDetailApiResponse> {
  const response = await developmentFetch(path, {
    method: "POST",
    credentials: "same-origin",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw scoringPolicyApiError(response);
  }
  return response.json() as Promise<ScoringConfigurationDetailApiResponse>;
}

export async function submitScoringConfiguration(
  payload: ScoringConfigurationSubmitPayload,
): Promise<ScoringConfigurationDetailApiResponse> {
  return postScoringPolicy("/api/v1/scoring-configurations", payload);
}

export async function decideScoringConfigurationApproval(
  approvalId: string,
  payload: { decision: "APPROVE" | "REJECT"; reason_code: string },
): Promise<ScoringConfigurationDetailApiResponse> {
  return postScoringPolicy(
    `/api/v1/scoring-configurations/approvals/${encodeURIComponent(approvalId)}/decision`,
    payload,
  );
}
