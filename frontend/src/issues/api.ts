import { developmentFetch } from '../development/fetch';
import type {
  GovernanceProjectionApiResponse,
  InvestigationEvidenceApiResponse,
  IssueAssigneeOptionsApiResponse,
  IssueListApiResponse,
  IssuePriority,
  LineageSnapshotApiResponse,
} from "./model";

export interface IssueCreatePayload {
  title: string;
  scope_type: "DATASET" | "SOURCE";
  scope_id: string;
  priority: IssuePriority;
  idempotency_key: string;
}

const CSRF_HEADER = "X-CSRF-Token";
let csrfProof: string | undefined;

export class IssueApiError extends Error {
  constructor(
    public readonly kind: "unauthorized" | "conflict" | "validation" | "technical",
    public readonly correlationId?: string,
  ) {
    super(
      correlationId
        ? `İşlem tamamlanamadı. Yeniden deneyin. İzleme kodu: ${correlationId}.`
        : "İşlem tamamlanamadı. Yeniden deneyin.",
    );
  }
}

export async function fetchIssues(signal?: AbortSignal): Promise<IssueListApiResponse> {
  const response = await developmentFetch("/api/v1/issues", {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new IssueApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      correlationId,
    );
  }
  const receivedProof = response.headers.get(CSRF_HEADER);
  if (receivedProof) csrfProof = receivedProof;
  return response.json() as Promise<IssueListApiResponse>;
}

export async function createIssue(
  payload: IssueCreatePayload,
): Promise<{
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: IssueListApiResponse["items"][number];
}> {
  if (!csrfProof) throw new IssueApiError("unauthorized");
  const response = await developmentFetch("/api/v1/issues", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      [CSRF_HEADER]: csrfProof,
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    const kind = response.status === 401 || response.status === 403
      ? "unauthorized"
      : response.status === 409
        ? "conflict"
        : response.status === 422
          ? "validation"
          : "technical";
    throw new IssueApiError(kind, correlationId);
  }
  return response.json();
}

export async function startIssueInvestigation(
  issueId: string,
  version: number,
): Promise<{
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: IssueListApiResponse["items"][number];
}> {
  if (!csrfProof) throw new IssueApiError("unauthorized");
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/investigation`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        [CSRF_HEADER]: csrfProof,
      },
      body: JSON.stringify({ version }),
    },
  );
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    const kind = response.status === 401 || response.status === 403
      ? "unauthorized"
      : response.status === 409
        ? "conflict"
        : response.status === 422
          ? "validation"
          : "technical";
    throw new IssueApiError(kind, correlationId);
  }
  return response.json();
}

export async function fetchIssueAssignmentOptions(
  issueId: string,
  signal?: AbortSignal,
): Promise<IssueAssigneeOptionsApiResponse> {
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/assignment-options`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  if (!response.ok) throw issueApiError(response);
  return response.json() as Promise<IssueAssigneeOptionsApiResponse>;
}

export async function reassignIssue(
  issueId: string,
  version: number,
  assigneeUserId: string,
  priority: IssuePriority,
): Promise<{
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: IssueListApiResponse["items"][number];
}> {
  if (!csrfProof) throw new IssueApiError("unauthorized");
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/assignment`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        [CSRF_HEADER]: csrfProof,
      },
      body: JSON.stringify({
        version,
        assignee_user_id: assigneeUserId,
        priority,
      }),
    },
  );
  if (!response.ok) throw issueApiError(response);
  return response.json();
}

export async function resolveIssue(
  issueId: string,
  version: number,
  rootCause: string,
  correctiveAction: string,
  evidenceReferenceId: string,
  completedAt: string,
): Promise<{
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: IssueListApiResponse["items"][number];
}> {
  if (!csrfProof) throw new IssueApiError("unauthorized");
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/resolution`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        [CSRF_HEADER]: csrfProof,
      },
      body: JSON.stringify({
        version,
        root_cause: rootCause,
        corrective_action: correctiveAction,
        evidence_reference_id: evidenceReferenceId,
        completed_at: completedAt,
      }),
    },
  );
  if (!response.ok) throw issueApiError(response);
  return response.json();
}

export async function verifyIssue(
  issueId: string,
  version: number,
  verificationReferenceId: string,
): Promise<{
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: IssueListApiResponse["items"][number];
}> {
  if (!csrfProof) throw new IssueApiError("unauthorized");
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/verification`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        [CSRF_HEADER]: csrfProof,
      },
      body: JSON.stringify({
        version,
        verification_reference_id: verificationReferenceId,
      }),
    },
  );
  if (!response.ok) throw issueApiError(response);
  return response.json();
}

export async function closeIssue(
  issueId: string,
  version: number,
): Promise<{
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: IssueListApiResponse["items"][number];
}> {
  if (!csrfProof) throw new IssueApiError("unauthorized");
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/closure`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        [CSRF_HEADER]: csrfProof,
      },
      body: JSON.stringify({ version }),
    },
  );
  if (!response.ok) throw issueApiError(response);
  return response.json();
}

function issueApiError(response: Response): IssueApiError {
  const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
  const kind = response.status === 401 || response.status === 403
    ? "unauthorized"
    : response.status === 409
      ? "conflict"
      : response.status === 422
        ? "validation"
        : "technical";
  return new IssueApiError(kind, correlationId);
}

// ---------------------------------------------------------------------------
// Evidence investigation API
// ---------------------------------------------------------------------------

export class EvidenceApiError extends Error {
  constructor(
    public readonly kind: "unauthorized" | "not-found" | "unavailable" | "technical",
    public readonly correlationId?: string,
  ) {
    super(
      kind === "unavailable"
        ? "Kanıt hizmeti şu anda kullanılamıyor."
        : kind === "unauthorized"
          ? "Bu kanıt için yetkiniz yok."
          : kind === "not-found"
            ? "İstenen kanıt bulunamadı."
            : "Kanıt yüklenemedi. Yeniden deneyin.",
    );
  }
}

export async function fetchLineageSnapshot(
  snapshotId: string,
  signal?: AbortSignal,
): Promise<LineageSnapshotApiResponse> {
  const response = await developmentFetch(
    `/api/v1/lineage/snapshots/${encodeURIComponent(snapshotId)}`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new EvidenceApiError(
      evidenceErrorKind(response.status),
      correlationId,
    );
  }
  return response.json() as Promise<LineageSnapshotApiResponse>;
}

export async function fetchGovernanceProjection(
  assetRef: string,
  signal?: AbortSignal,
): Promise<GovernanceProjectionApiResponse> {
  const response = await developmentFetch(
    `/api/v1/governance/${encodeURIComponent(assetRef)}/projection`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new EvidenceApiError(
      evidenceErrorKind(response.status),
      correlationId,
    );
  }
  return response.json() as Promise<GovernanceProjectionApiResponse>;
}

export async function fetchInvestigationEvidence(
  issueId: string,
  signal?: AbortSignal,
): Promise<InvestigationEvidenceApiResponse> {
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/investigation/evidence`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new EvidenceApiError(
      evidenceErrorKind(response.status),
      correlationId,
    );
  }
  return response.json() as Promise<InvestigationEvidenceApiResponse>;
}

function evidenceErrorKind(
  status: number,
): EvidenceApiError["kind"] {
  if (status === 401 || status === 403) return "unauthorized";
  if (status === 404) return "not-found";
  if (status === 503) return "unavailable";
  return "technical";
}
