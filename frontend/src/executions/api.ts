import type {
  ExecutionDetailApiResponse,
  ExecutionListApiResponse,
  ExecutionStartRequest,
  ExecutionCancelRequest,
} from "./model";
import { developmentFetch } from "../development/fetch";

export type ExecutionErrorKind =
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "governance_approval_required"
  | "validation"
  | "technical";

export class ExecutionApiError extends Error {
  constructor(
    public readonly kind: ExecutionErrorKind,
    public readonly correlationId?: string,
    public readonly governanceRequestType?: string,
  ) {
    super("Execution request failed.");
  }
}

function classifyStatus(status: number): ExecutionErrorKind {
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 404) return "not_found";
  if (status === 409) return "conflict";
  if (status === 422) return "validation";
  return "technical";
}

async function classifyError(response: Response): Promise<ExecutionApiError> {
  const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
  if (response.status === 409) {
    try {
      const body = (await response.json()) as {
        code?: string;
        governance_request_type?: string;
      };
      if (body?.code === "EXECUTION_GOVERNANCE_APPROVAL_REQUIRED") {
        return new ExecutionApiError(
          "governance_approval_required",
          correlationId,
          body.governance_request_type,
        );
      }
    } catch {
      // Gövde JSON değilse jenerik conflict olarak sınıflandır.
    }
  }
  return new ExecutionApiError(classifyStatus(response.status), correlationId);
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw await classifyError(response);
  }
  return response.json() as Promise<T>;
}

export interface ExecutionFilterParams {
  datasetId?: string;
  scheduleId?: string;
}

export async function fetchExecutions(
  signalOrFilters?: AbortSignal | ExecutionFilterParams,
  extraSignal?: AbortSignal,
): Promise<ExecutionListApiResponse> {
  const filters: ExecutionFilterParams | undefined =
    signalOrFilters && "datasetId" in signalOrFilters ? signalOrFilters : undefined;
  const signal = signalOrFilters instanceof AbortSignal ? signalOrFilters : extraSignal;
  const params = new URLSearchParams();
  if (filters?.datasetId) params.set("dataset_id", filters.datasetId);
  if (filters?.scheduleId) params.set("schedule_id", filters.scheduleId);
  const query = params.toString();
  const url = query ? `/api/v1/executions?${query}` : "/api/v1/executions";
  const response = await developmentFetch(url, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  return handleResponse<ExecutionListApiResponse>(response);
}

export async function fetchExecutionDetail(
  executionId: string,
  signal?: AbortSignal,
): Promise<ExecutionDetailApiResponse> {
  const response = await developmentFetch(`/api/v1/executions/${executionId}`, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  return handleResponse<ExecutionDetailApiResponse>(response);
}

export async function startExecution(
  payload: ExecutionStartRequest,
): Promise<ExecutionListApiResponse["items"][number]> {
  const response = await developmentFetch("/api/v1/executions", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await handleResponse<{ item: ExecutionListApiResponse["items"][number] }>(response);
  return data.item;
}

export async function cancelExecution(
  executionId: string,
  payload: ExecutionCancelRequest,
): Promise<ExecutionListApiResponse["items"][number]> {
  const response = await developmentFetch(`/api/v1/executions/${executionId}/cancel`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await handleResponse<{ item: ExecutionListApiResponse["items"][number] }>(response);
  return data.item;
}
