import type {
  ScheduleCreatedApiResponse,
  ScheduleCreatePayload,
  ScheduleListApiResponse,
  ScheduleProposalApiResponse,
} from "./model";
import { developmentFetch } from "../development/fetch";

export type JobErrorKind =
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "governance_approval_required"
  | "validation"
  | "technical";

export class JobsApiError extends Error {
  constructor(
    public readonly kind: JobErrorKind,
    public readonly detail: string,
    public readonly correlationId?: string,
    public readonly governanceRequestType?: string,
  ) {
    super(detail);
  }
}

function classifyStatus(status: number): JobErrorKind {
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 404) return "not_found";
  if (status === 409) return "conflict";
  if (status === 422) return "validation";
  return "technical";
}

async function classifyError(response: Response): Promise<JobsApiError> {
  const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
  let detail = "The schedule request could not be completed.";
  let body: { detail?: string | unknown[]; code?: string; governance_request_type?: string } = {};
  try {
    body = (await response.json()) as typeof body;
    if (typeof body?.detail === "string") {
      detail = body.detail;
    } else if (Array.isArray(body?.detail) && body.detail.length > 0) {
      detail = body.detail
        .map((entry) => {
          if (typeof entry === "string") return entry;
          if (entry && typeof entry === "object" && "msg" in entry) {
            const fieldPath = Array.isArray((entry as Record<string, unknown>).loc)
              ? ((entry as Record<string, unknown>).loc as unknown[]).join(".")
              : "";
            return fieldPath ? `${fieldPath}: ${String((entry as Record<string, unknown>).msg)}` : String((entry as Record<string, unknown>).msg);
          }
          return String(entry);
        })
        .join("; ");
    }
  } catch {
    // Gövde JSON değilse güvenli varsayılana düş.
  }
  if (
    response.status === 409 &&
    body?.code === "EXECUTION_GOVERNANCE_APPROVAL_REQUIRED"
  ) {
    return new JobsApiError(
      "governance_approval_required",
      detail,
      correlationId,
      body.governance_request_type,
    );
  }
  return new JobsApiError(classifyStatus(response.status), detail, correlationId);
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw await classifyError(response);
  }
  return response.json() as Promise<T>;
}

export async function fetchSchedules(signal?: AbortSignal): Promise<ScheduleListApiResponse> {
  const response = await developmentFetch("/api/v1/schedules", {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  return handleResponse<ScheduleListApiResponse>(response);
}

export async function fetchScheduleProposals(
  datasetId: string,
  signal?: AbortSignal,
): Promise<ScheduleProposalApiResponse> {
  const response = await developmentFetch(
    `/api/v1/datasets/${encodeURIComponent(datasetId)}/schedule-proposals`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  return handleResponse<ScheduleProposalApiResponse>(response);
}

export async function createSchedule(
  payload: ScheduleCreatePayload,
): Promise<ScheduleCreatedApiResponse> {
  const response = await developmentFetch("/api/v1/schedules", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse<ScheduleCreatedApiResponse>(response);
}

export async function setScheduleActive(
  scheduleId: string,
  active: boolean,
): Promise<ScheduleListApiResponse["items"][number]> {
  const action = active ? "activate" : "deactivate";
  const response = await developmentFetch(`/api/v1/schedules/${encodeURIComponent(scheduleId)}/${action}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  return handleResponse<ScheduleListApiResponse["items"][number]>(response);
}
