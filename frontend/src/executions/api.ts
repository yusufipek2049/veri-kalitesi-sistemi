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
  | "validation"
  | "technical";

export class ExecutionApiError extends Error {
  constructor(
    public readonly kind: ExecutionErrorKind,
    public readonly correlationId?: string,
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

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new ExecutionApiError(classifyStatus(response.status), correlationId);
  }
  return response.json() as Promise<T>;
}

export async function fetchExecutions(signal?: AbortSignal): Promise<ExecutionListApiResponse> {
  const response = await developmentFetch("/api/v1/executions", {
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
