import type { DataSourceListApiResponse } from "./model";

export class DataSourceApiError extends Error {
  constructor(
    public readonly kind: "unauthorized" | "technical",
    public readonly correlationId?: string,
  ) {
    super("Data source list request failed.");
  }
}

export async function fetchDataSources(signal?: AbortSignal): Promise<DataSourceListApiResponse> {
  const response = await fetch("/api/v1/data-sources", {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new DataSourceApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      correlationId,
    );
  }
  return response.json() as Promise<DataSourceListApiResponse>;
}
