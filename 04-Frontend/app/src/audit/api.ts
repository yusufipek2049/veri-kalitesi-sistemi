import type { AuditEventListApiResponse, AuditQueryFilters } from "./model";
import { developmentFetch } from "../development/fetch";

export class AuditApiError extends Error {
  constructor(
    public readonly kind: "unauthorized" | "technical",
    public readonly correlationId?: string,
  ) {
    super("Audit event request failed.");
  }
}

export async function fetchAuditEvents(
  filters: AuditQueryFilters,
  options: {
    afterSequenceNo?: number;
    periodEnd?: string;
    throughSequenceNo?: number;
    signal?: AbortSignal;
  } = {},
): Promise<AuditEventListApiResponse> {
  const params = new URLSearchParams({ days: String(filters.days), page_size: "50" });
  if (filters.actorId.trim()) params.set("actor_id", filters.actorId.trim());
  if (filters.action.trim()) params.set("action", filters.action.trim());
  if (filters.objectType.trim()) params.set("object_type", filters.objectType.trim());
  if (filters.result !== "ALL") params.set("result", filters.result);
  if (options.afterSequenceNo !== undefined) {
    params.set("after_sequence_no", String(options.afterSequenceNo));
  }
  if (options.periodEnd !== undefined) params.set("period_end", options.periodEnd);
  if (options.throughSequenceNo !== undefined) {
    params.set("through_sequence_no", String(options.throughSequenceNo));
  }
  const response = await developmentFetch(`/api/v1/audit/events?${params.toString()}`, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal: options.signal,
  });
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new AuditApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      correlationId,
    );
  }
  return response.json() as Promise<AuditEventListApiResponse>;
}
