import type {
  CatalogDatasetListApiResponse,
  CatalogDatasetDetailApiResponse,
  CatalogFieldListApiResponse,
  CatalogFieldDetailApiResponse,
  DatasetPreviewApiResponse,
  DiscoveryStatusApiResponse,
  DiscoveryResponse,
  DiscoveryDiffApiResponse,
  DatasetUpdatePayload,
  FieldUpdatePayload,
} from "./model";
import { developmentFetch } from "../development/fetch";

interface ProblemBody {
  detail?: string;
  correlation_id?: string;
}

export class CatalogApiError extends Error {
  constructor(
    public readonly httpStatus: number,
    public readonly detail: string,
    public readonly correlationId?: string,
  ) {
    super(detail);
  }

  get kind(): "unauthorized" | "not-found" | "conflict" | "validation" | "technical" {
    if (this.httpStatus === 401 || this.httpStatus === 403) return "unauthorized";
    if (this.httpStatus === 404) return "not-found";
    if (this.httpStatus === 409) return "conflict";
    if (this.httpStatus === 400 || this.httpStatus === 422) return "validation";
    return "technical";
  }
}

async function catalogApiError(response: Response): Promise<CatalogApiError> {
  let body: ProblemBody = {};
  try {
    body = (await response.json()) as ProblemBody;
  } catch {
    // Non-JSON responses use the safe fallback below.
  }
  const correlationId =
    body.correlation_id ??
    response.headers.get("X-Correlation-ID") ??
    undefined;
  return new CatalogApiError(
    response.status,
    body.detail ?? "The catalog request could not be completed.",
    correlationId,
  );
}

// ── GET endpoints ───────────────────────────────────────────────────

export async function listCatalogDatasets(params?: {
  status?: string;
  nameContains?: string;
  limit?: number;
}, signal?: AbortSignal): Promise<CatalogDatasetListApiResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.nameContains) searchParams.set("name_contains", params.nameContains);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  const query = searchParams.toString();
  const url = `/api/v1/datasets${query ? `?${query}` : ""}`;
  const response = await developmentFetch(url, { signal });
  if (!response.ok) throw await catalogApiError(response);
  return (await response.json()) as CatalogDatasetListApiResponse;
}

export async function getCatalogDataset(
  datasetId: string,
): Promise<CatalogDatasetDetailApiResponse> {
  const response = await developmentFetch(`/api/v1/datasets/${encodeURIComponent(datasetId)}`);
  if (!response.ok) throw await catalogApiError(response);
  return (await response.json()) as CatalogDatasetDetailApiResponse;
}

export async function listCatalogFields(
  datasetId: string,
): Promise<CatalogFieldListApiResponse> {
  const response = await developmentFetch(
    `/api/v1/datasets/${encodeURIComponent(datasetId)}/fields`,
  );
  if (!response.ok) throw await catalogApiError(response);
  return (await response.json()) as CatalogFieldListApiResponse;
}

export async function getCatalogField(
  fieldId: string,
): Promise<CatalogFieldDetailApiResponse> {
  const response = await developmentFetch(`/api/v1/fields/${encodeURIComponent(fieldId)}`);
  if (!response.ok) throw await catalogApiError(response);
  return (await response.json()) as CatalogFieldDetailApiResponse;
}

export async function getDatasetPreview(
  datasetId: string,
  limit = 50,
  signal?: AbortSignal,
): Promise<DatasetPreviewApiResponse> {
  const response = await developmentFetch(
    `/api/v1/datasets/${encodeURIComponent(datasetId)}/preview?limit=${limit}`,
    { signal },
  );
  if (!response.ok) throw await catalogApiError(response);
  return (await response.json()) as DatasetPreviewApiResponse;
}

export async function getDiscoveryStatus(
  discoveryId: number,
): Promise<DiscoveryStatusApiResponse> {
  const response = await developmentFetch(
    `/api/v1/metadata-discoveries/${discoveryId}`,
  );
  if (!response.ok) throw await catalogApiError(response);
  return (await response.json()) as DiscoveryStatusApiResponse;
}

export async function getDiscoveryDiff(
  discoveryId: number,
): Promise<DiscoveryDiffApiResponse> {
  const response = await developmentFetch(
    `/api/v1/metadata-discoveries/${discoveryId}/diff`,
  );
  if (!response.ok) throw await catalogApiError(response);
  return (await response.json()) as DiscoveryDiffApiResponse;
}

/**
 * Poll discovery status until terminal state or timeout.
 * Terminal states: SUCCESS, PARTIAL, TECHNICAL_ERROR, CANCELLED
 */
export async function pollDiscoveryStatus(
  discoveryId: number,
  options: {
    intervalMs?: number;
    timeoutMs?: number;
    signal?: AbortSignal;
    onProgress?: (status: DiscoveryStatusApiResponse) => void;
  } = {},
): Promise<DiscoveryStatusApiResponse> {
  const intervalMs = options.intervalMs ?? 3000;
  const timeoutMs = options.timeoutMs ?? 60_000;
  const terminalStates = new Set(["SUCCESS", "PARTIAL", "TECHNICAL_ERROR", "CANCELLED"]);
  const startTime = Date.now();

  return new Promise((resolve, reject) => {
    const poll = async () => {
      if (options.signal?.aborted) {
        reject(new DOMException("Polling aborted", "AbortError"));
        return;
      }
      if (Date.now() - startTime > timeoutMs) {
        reject(new Error("Discovery polling timed out."));
        return;
      }
      try {
        const status = await getDiscoveryStatus(discoveryId);
        options.onProgress?.(status);
        if (terminalStates.has(status.status)) {
          resolve(status);
          return;
        }
      } catch (error) {
        reject(error);
        return;
      }
      setTimeout(poll, intervalMs);
    };
    void poll();
  });
}

// ── Command endpoints ───────────────────────────────────────────────

export async function requestMetadataDiscovery(
  dataSourceId: string,
  idempotencyKey?: string,
): Promise<DiscoveryResponse> {
  const response = await developmentFetch(
    `/api/v1/data-sources/${encodeURIComponent(dataSourceId)}/metadata-discoveries`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idempotency_key: idempotencyKey ?? null }),
    },
  );
  if (!response.ok) throw await catalogApiError(response);
  return (await response.json()) as DiscoveryResponse;
}

// ── PATCH endpoints (catalog editing) ───────────────────────────────

export async function updateDataset(
  datasetId: string,
  payload: DatasetUpdatePayload,
): Promise<CatalogDatasetDetailApiResponse> {
  const response = await developmentFetch(
    `/api/v1/datasets/${encodeURIComponent(datasetId)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) throw await catalogApiError(response);
  return (await response.json()) as CatalogDatasetDetailApiResponse;
}

export async function updateField(
  fieldId: string,
  payload: FieldUpdatePayload,
): Promise<CatalogFieldDetailApiResponse> {
  const response = await developmentFetch(
    `/api/v1/fields/${encodeURIComponent(fieldId)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) throw await catalogApiError(response);
  return (await response.json()) as CatalogFieldDetailApiResponse;
}
