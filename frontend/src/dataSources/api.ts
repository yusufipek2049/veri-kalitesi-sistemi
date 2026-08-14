import type {
  DataSourceCreateRequest,
  DataSourceListApiResponse,
  DataSourceMutationApiResponse,
} from "./model";
import { developmentFetch } from "../development/fetch";

interface ProblemBody {
  code?: string;
  detail?: string;
  correlation_id?: string;
}

export class DataSourceApiError extends Error {
  constructor(
    public readonly httpStatus: number,
    public readonly code: string,
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

async function dataSourceApiError(response: Response): Promise<DataSourceApiError> {
  let body: ProblemBody = {};
  try {
    body = await response.json() as ProblemBody;
  } catch {
    // Non-JSON upstream responses use the safe fallback below.
  }
  const correlationId = body.correlation_id
    ?? response.headers.get("X-Correlation-ID")
    ?? undefined;
  return new DataSourceApiError(
    response.status,
    body.code ?? "DATA_SOURCE_UNKNOWN_ERROR",
    body.detail ?? "The data source action could not be completed safely.",
    correlationId,
  );
}

async function command(
  path: string,
  body?: Record<string, unknown> | DataSourceCreateRequest,
): Promise<DataSourceMutationApiResponse> {
  const response = await developmentFetch(path, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw await dataSourceApiError(response);
  return response.json() as Promise<DataSourceMutationApiResponse>;
}

export async function fetchDataSources(
  signal?: AbortSignal,
): Promise<DataSourceListApiResponse> {
  const response = await developmentFetch("/api/v1/data-sources", {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) throw await dataSourceApiError(response);
  return response.json() as Promise<DataSourceListApiResponse>;
}

export function createDataSource(
  payload: DataSourceCreateRequest,
): Promise<DataSourceMutationApiResponse> {
  return command("/api/v1/data-sources", payload);
}

export function testDataSource(dataSourceId: string): Promise<DataSourceMutationApiResponse> {
  return command(`/api/v1/data-sources/${encodeURIComponent(dataSourceId)}/test`);
}

export function requestDataSourceActivation(
  dataSourceId: string,
): Promise<DataSourceMutationApiResponse> {
  return command(`/api/v1/data-sources/${encodeURIComponent(dataSourceId)}/activation`);
}

export function decideDataSourceActivation(
  activationRequestId: string,
  decision: "APPROVE" | "REJECT",
  reasonCode: string,
): Promise<DataSourceMutationApiResponse> {
  return command(
    `/api/v1/data-source-activation-requests/${encodeURIComponent(activationRequestId)}/decision`,
    { decision, reason_code: reasonCode },
  );
}

export function passivateDataSource(
  dataSourceId: string,
  reasonCode: string,
): Promise<DataSourceMutationApiResponse> {
  return command(
    `/api/v1/data-sources/${encodeURIComponent(dataSourceId)}/passivation`,
    { reason_code: reasonCode },
  );
}

export function requestDataSourceDeactivation(
  dataSourceId: string,
): Promise<DataSourceMutationApiResponse> {
  return command(`/api/v1/data-sources/${encodeURIComponent(dataSourceId)}/deactivation`);
}

export function decideDataSourceDeactivation(
  deactivationRequestId: string,
  decision: "APPROVE" | "REJECT",
  reasonCode: string,
): Promise<DataSourceMutationApiResponse> {
  return command(
    `/api/v1/data-source-deactivation-requests/${encodeURIComponent(deactivationRequestId)}/decision`,
    { decision, reason_code: reasonCode },
  );
}

export interface DiscoveryApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  discovery_id: number;
  data_source_id: string;
  status: string;
  job_id: string | null;
}

export function discoverMetadata(
  dataSourceId: string,
): Promise<DiscoveryApiResponse> {
  return command(
    `/api/v1/data-sources/${encodeURIComponent(dataSourceId)}/metadata-discoveries`,
  ) as unknown as Promise<DiscoveryApiResponse>;
}

export function dataSourceErrorMessage(error: unknown): string {
  if (!(error instanceof DataSourceApiError)) return "İşlem güvenli biçimde tamamlanamadı.";
  const messages: Record<string, string> = {
    DATA_SOURCE_PERMISSION_DENIED: "Bu işlem için rol veya kapsam yetkiniz bulunmuyor.",
    DATA_SOURCE_MAKER_CHECKER_VIOLATION: "Kendi aktivasyon talebinizi onaylayamazsınız.",
    DATA_SOURCE_NOT_FOUND: "Veri kaynağı bulunamadı; listeyi yenileyin.",
    ACTIVATION_REQUEST_NOT_FOUND: "Aktivasyon talebi bulunamadı; listeyi yenileyin.",
    DATA_SOURCE_STATE_CONFLICT: "Kaynağın durumu değişti; listeyi yenileyip tekrar deneyin.",
    DATA_SOURCE_REVISION_CONFLICT: "Kaynağın sürümü değişti; listeyi yenileyin.",
    DATA_SOURCE_DECISION_CONFLICT: "Aktivasyon talebi daha önce farklı bir kararla tamamlanmış.",
    DATA_SOURCE_PENDING_ACTIVATION_EXISTS: "Bu sürüm için zaten bekleyen bir aktivasyon talebi var.",
    DATA_SOURCE_POLICY_CONFLICT: "Yetki politikası değişti; listeyi yenileyin.",
    DATA_SOURCE_ACTIVATION_EXPIRED: "Aktivasyon talebinin süresi dolmuş; yeni talep oluşturun.",
    DATA_SOURCE_SECRET_UNAVAILABLE: "Kimlik bilgisi referansına şu anda erişilemiyor.",
    DATA_SOURCE_PERSISTENCE_UNAVAILABLE: "Veri kaynağı deposuna şu anda erişilemiyor.",
    DATA_SOURCE_AUDIT_UNAVAILABLE: "Audit kaydı tamamlanamadığı için işlem güvenli biçimde sonuçlandırılamadı.",
    DATA_SOURCE_SERVICE_UNAVAILABLE: "Veri kaynağı servisine şu anda erişilemiyor.",
    DATA_SOURCE_INPUT_INVALID: "Gönderilen alanları kontrol edin.",
    DATA_SOURCE_DOMAIN_VALIDATION_FAILED: "Veri kaynağı bilgileri iş kurallarını karşılamıyor.",
  };
  const base = messages[error.code] ?? "İşlem güvenli biçimde tamamlanamadı.";
  return error.correlationId ? `${base} İzleme kodu: ${error.correlationId}.` : base;
}
