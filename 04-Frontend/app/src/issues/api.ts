import type {
  IssueAssigneeOptionsApiResponse,
  IssueListApiResponse,
  IssuePriority,
} from "./model";

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
  const response = await fetch("/api/v1/issues", {
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
  const response = await fetch(
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
  const response = await fetch(
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
  const response = await fetch(
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
  const response = await fetch(
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
