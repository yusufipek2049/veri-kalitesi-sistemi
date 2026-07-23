import type { IssueListApiResponse } from "./model";

export class IssueApiError extends Error {
  constructor(
    public readonly kind: "unauthorized" | "technical",
    public readonly correlationId?: string,
  ) {
    super("Issue list request failed.");
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
  return response.json() as Promise<IssueListApiResponse>;
}
