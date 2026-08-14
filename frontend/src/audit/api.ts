import type {
  AuditEventListApiResponse,
  AuditQueryFilters,
  AuditSummaryResponse,
} from "./model";
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
  const params = auditQueryParams(filters, true);
  params.set("page_size", "50");
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

/**
 * @deprecated Kullanılmayan — yalnızca test referansı. UI'ya bağlanmadı.
 * İlgili endpoint: GET /api/v1/audit/events/grouped. Bağlanmayacaksa kaldırılabilir.
 */
export async function fetchGroupedAuditEvents(
  correlationId: string,
): Promise<AuditEventListApiResponse> {
  const params = new URLSearchParams({ correlation_id: correlationId });
  const response = await developmentFetch(
    `/api/v1/audit/events/grouped?${params.toString()}`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    },
  );
  if (!response.ok) {
    const responseCorrelationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new AuditApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      responseCorrelationId,
    );
  }
  return response.json() as Promise<AuditEventListApiResponse>;
}

export async function fetchAuditSummary(
  filters: AuditQueryFilters,
  options: { signal?: AbortSignal } = {},
): Promise<AuditSummaryResponse> {
  const params = auditQueryParams(filters, false);
  const response = await developmentFetch(`/api/v1/audit/summary?${params.toString()}`, {
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
  return response.json() as Promise<AuditSummaryResponse>;
}

export async function fetchAuditExport(
  filters: AuditQueryFilters,
  format: "csv" | "json",
): Promise<Blob> {
  const params = auditQueryParams(filters, true);
  params.set("format", format);
  const response = await developmentFetch(
    `/api/v1/audit/events/export?${params.toString()}`,
    {
      credentials: "same-origin",
      headers: { Accept: format === "csv" ? "text/csv" : "application/json" },
    },
  );
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new AuditApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      correlationId,
    );
  }
  return response.blob();
}

function auditQueryParams(
  filters: AuditQueryFilters,
  includeCorrelation: boolean,
): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.periodStart) {
    params.set("period_start", filters.periodStart);
    if (filters.periodEnd) params.set("period_end", filters.periodEnd);
  } else {
    params.set("days", String(filters.days));
  }
  if (filters.actorId.trim()) params.set("actor_id", filters.actorId.trim());
  if (filters.action.trim()) params.set("action", filters.action.trim());
  if (filters.objectType.trim()) params.set("object_type", filters.objectType.trim());
  if (filters.objectId.trim()) params.set("object_id", filters.objectId.trim());
  if (filters.result !== "ALL") params.set("result", filters.result);
  if (includeCorrelation && filters.correlationId.trim()) {
    params.set("correlation_id", filters.correlationId.trim());
  }
  return params;
}
