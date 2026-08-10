import type {
  CatalogDatasetListApiResponse,
  CatalogDatasetDetailApiResponse,
  CatalogFieldListApiResponse,
  CatalogFieldDetailApiResponse,
  DiscoveryStatusApiResponse,
  DiscoveryResponse,
  DiffApplicationApiResponse,
} from "./model";
import { developmentFetch } from "../development/fetch";

const CSRF_HEADER = "X-CSRF-Token";
let csrfProof: string | undefined;

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

function commandHeaders(): Record<string, string> {
  if (!csrfProof) {
    throw new CatalogApiError(
      401,
      "CATALOG_CSRF_PROOF_MISSING",
      "A fresh data source list must be loaded before changing state.",
    );
  }
  return { [CSRF_HEADER]: csrfProof, "Content-Type": "application/json" };
}

// ── GET endpoints ───────────────────────────────────────────────────

export async function listCatalogDatasets(params?: {
  status?: string;
  nameContains?: string;
  limit?: number;
}): Promise<CatalogDatasetListApiResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.nameContains) searchParams.set("name_contains", params.nameContains);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  const query = searchParams.toString();
  const url = `/api/v1/datasets${query ? `?${query}` : ""}`;
  const response = await developmentFetch(url);
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

export async function getDiscoveryStatus(
  discoveryId: number,
): Promise<DiscoveryStatusApiResponse> {
  const response = await developmentFetch(
    `/api/v1/metadata-discoveries/${discoveryId}`,
  );
  if (!response.ok) throw await catalogApiError(response);
  return (await response.json()) as DiscoveryStatusApiResponse;
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
      headers: commandHeaders(),
      body: JSON.stringify({ idempotency_key: idempotencyKey ?? null }),
    },
  );
  if (!response.ok) throw await catalogApiError(response);
  return (await response.json()) as DiscoveryResponse;
}

export async function applyMetadataDiff(
  metadataDiffId: string,
  payload: { reason_code: string; expected_version: number },
): Promise<DiffApplicationApiResponse> {
  const response = await developmentFetch(
    `/api/v1/metadata-diffs/${encodeURIComponent(metadataDiffId)}/application`,
    {
      method: "POST",
      headers: commandHeaders(),
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) throw await catalogApiError(response);
  return (await response.json()) as DiffApplicationApiResponse;
}
