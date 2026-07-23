import type { ExecutionListApiResponse } from "./model";

export class ExecutionApiError extends Error {
  constructor(
    public readonly kind: "unauthorized" | "technical",
    public readonly correlationId?: string,
  ) {
    super("Execution list request failed.");
  }
}

export async function fetchExecutions(signal?: AbortSignal): Promise<ExecutionListApiResponse> {
  const response = await fetch("/api/v1/executions", {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new ExecutionApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      correlationId,
    );
  }
  return response.json() as Promise<ExecutionListApiResponse>;
}
