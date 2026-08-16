import { developmentFetch } from "../development/fetch";
import type {
  GovernanceListApiResponse,
  GovernanceApprovalApiItem,
  GovernanceView,
} from "./model";

export class GovernanceApiError extends Error {
  constructor(
    public readonly kind: "unauthorized" | "conflict" | "validation" | "technical",
    public readonly correlationId?: string,
  ) {
    super(
      kind === "unauthorized"
        ? correlationId
          ? `Bu yönetişim işlemi için yetkiniz yok. İzleme kodu: ${correlationId}.`
          : "Bu yönetişim işlemi için yetkiniz yok."
        : correlationId
          ? `Yönetişim işlemi tamamlanamadı. Yeniden deneyin. İzleme kodu: ${correlationId}.`
          : "Yönetişim işlemi tamamlanamadı. Yeniden deneyin.",
    );
  }
}

function governanceApiError(response: Response): GovernanceApiError {
  const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
  const kind =
    response.status === 401 || response.status === 403
      ? "unauthorized"
      : response.status === 409
        ? "conflict"
        : response.status === 422
          ? "validation"
          : "technical";
  return new GovernanceApiError(kind, correlationId);
}

export async function fetchGovernanceApprovals(
  view: GovernanceView,
  signal?: AbortSignal,
): Promise<GovernanceListApiResponse> {
  const response = await developmentFetch(
    `/api/v1/governance/approval-requests?view=${encodeURIComponent(view)}`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  if (!response.ok) {
    throw governanceApiError(response);
  }
  return response.json() as Promise<GovernanceListApiResponse>;
}

interface GovernanceDetailApiResponse {
  api_version: string;
  data_origin: string;
  correlation_id: string;
  item: GovernanceApprovalApiItem;
}

async function postGovernance(
  path: string,
  body: Record<string, unknown> | null,
): Promise<GovernanceDetailApiResponse> {
  const response = await developmentFetch(path, {
    method: "POST",
    credentials: "same-origin",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: body === null ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    throw governanceApiError(response);
  }
  return response.json() as Promise<GovernanceDetailApiResponse>;
}

export async function createGovernanceApproval(payload: {
  request_type: string;
  object_id: string;
  reason_code: string;
  new_owner_user_id?: string;
  proposed_changes?: Record<string, unknown>;
}): Promise<GovernanceDetailApiResponse> {
  return postGovernance("/api/v1/governance/approval-requests", payload);
}

export async function decideGovernanceApproval(
  approvalRequestId: string,
  payload: { decision: "APPROVE" | "REJECT"; reason_code: string },
): Promise<GovernanceDetailApiResponse> {
  return postGovernance(
    `/api/v1/governance/approval-requests/${encodeURIComponent(approvalRequestId)}/decision`,
    payload,
  );
}

export async function withdrawGovernanceApproval(
  approvalRequestId: string,
  payload: { reason_code: string },
): Promise<GovernanceDetailApiResponse> {
  return postGovernance(
    `/api/v1/governance/approval-requests/${encodeURIComponent(approvalRequestId)}/withdraw`,
    payload,
  );
}

export async function applyGovernanceApproval(
  approvalRequestId: string,
): Promise<GovernanceDetailApiResponse> {
  return postGovernance(
    `/api/v1/governance/approval-requests/${encodeURIComponent(approvalRequestId)}/apply`,
    null,
  );
}
