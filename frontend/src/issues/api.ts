import {
  developmentFetch,
  recordCsrfProof,
  stateChangingHeaders,
} from '../development/fetch';
import type {
  InvestigationEvidenceApiResponse,
  IssueAssigneeOptionsApiResponse,
  IssueEvidenceApiItem,
  IssueEvidenceListApiResponse,
  IssueListApiResponse,
  IssuePriority,
} from "./model";

export interface IssueCreatePayload {
  title: string;
  scope_type: "DATASET" | "SOURCE";
  scope_id: string;
  priority: IssuePriority;
  idempotency_key: string;
}

export class IssueApiError extends Error {
  constructor(
    public readonly kind: "unauthorized" | "conflict" | "validation" | "technical",
    public readonly correlationId?: string,
  ) {
    super(
      correlationId
        ? `İşlem tamamlanamadı. Yeniden deneyin. İzleme kodu: ${correlationId}.`
        : "İşlem tamamlanamadı. Yeniden deneyin.",
    );
  }
}

export async function fetchIssues(signal?: AbortSignal): Promise<IssueListApiResponse> {
  const response = await developmentFetch("/api/v1/issues", {
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

export async function createIssue(
  payload: IssueCreatePayload,
): Promise<{
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: IssueListApiResponse["items"][number];
}> {
  const response = await developmentFetch("/api/v1/issues", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    const kind = response.status === 401 || response.status === 403
      ? "unauthorized"
      : response.status === 409
        ? "conflict"
        : response.status === 422
          ? "validation"
          : "technical";
    throw new IssueApiError(kind, correlationId);
  }
  return response.json();
}

export async function startIssueInvestigation(
  issueId: string,
  version: number,
): Promise<{
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: IssueListApiResponse["items"][number];
}> {
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/investigation`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ version }),
    },
  );
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    const kind = response.status === 401 || response.status === 403
      ? "unauthorized"
      : response.status === 409
        ? "conflict"
        : response.status === 422
          ? "validation"
          : "technical";
    throw new IssueApiError(kind, correlationId);
  }
  return response.json();
}

export async function fetchIssueAssignmentOptions(
  issueId: string,
  signal?: AbortSignal,
): Promise<IssueAssigneeOptionsApiResponse> {
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/assignment-options`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  if (!response.ok) throw issueApiError(response);
  return response.json() as Promise<IssueAssigneeOptionsApiResponse>;
}

export async function reassignIssue(
  issueId: string,
  version: number,
  assigneeUserId: string,
  priority: IssuePriority,
): Promise<{
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: IssueListApiResponse["items"][number];
}> {
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/assignment`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        version,
        assignee_user_id: assigneeUserId,
        priority,
      }),
    },
  );
  if (!response.ok) throw issueApiError(response);
  return response.json();
}

export async function resolveIssue(
  issueId: string,
  version: number,
  rootCause: string,
  correctiveAction: string,
  evidenceReferenceId: string,
  completedAt: string,
): Promise<{
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: IssueListApiResponse["items"][number];
}> {
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/resolution`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        version,
        root_cause: rootCause,
        corrective_action: correctiveAction,
        evidence_reference_id: evidenceReferenceId,
        completed_at: completedAt,
      }),
    },
  );
  if (!response.ok) throw issueApiError(response);
  return response.json();
}

export async function verifyIssue(
  issueId: string,
  version: number,
  verificationReferenceId: string,
): Promise<{
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: IssueListApiResponse["items"][number];
}> {
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/verification`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        version,
        verification_reference_id: verificationReferenceId,
      }),
    },
  );
  if (!response.ok) throw issueApiError(response);
  return response.json();
}

export async function closeIssue(
  issueId: string,
  version: number,
): Promise<{
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: IssueListApiResponse["items"][number];
}> {
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/closure`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ version }),
    },
  );
  if (!response.ok) throw issueApiError(response);
  return response.json();
}

function issueApiError(response: Response): IssueApiError {
  const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
  const kind = response.status === 401 || response.status === 403
    ? "unauthorized"
    : response.status === 409
      ? "conflict"
      : response.status === 422
        ? "validation"
        : "technical";
  return new IssueApiError(kind, correlationId);
}

// ---------------------------------------------------------------------------
// Evidence investigation API
// ---------------------------------------------------------------------------

export class EvidenceApiError extends Error {
  constructor(
    public readonly kind: "unauthorized" | "not-found" | "unavailable" | "technical",
    public readonly correlationId?: string,
  ) {
    super(
      kind === "unavailable"
        ? "Kanıt hizmeti şu anda kullanılamıyor."
        : kind === "unauthorized"
          ? "Bu kanıt için yetkiniz yok."
          : kind === "not-found"
            ? "İstenen kanıt bulunamadı."
            : "Kanıt yüklenemedi. Yeniden deneyin.",
    );
  }
}

/**
 * @deprecated Kullanılmayan — yalnızca test referansı. UI'ya bağlanmadı.
 * İlgili endpoint: GET /api/v1/issues/{id}/investigation/evidence.
 * Sorun detay görünümüne entegre edilebilir; aksi halde kaldırılabilir.
 */
export async function fetchInvestigationEvidence(
  issueId: string,
  signal?: AbortSignal,
): Promise<InvestigationEvidenceApiResponse> {
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/investigation/evidence`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new EvidenceApiError(
      evidenceErrorKind(response.status),
      correlationId,
    );
  }
  return response.json() as Promise<InvestigationEvidenceApiResponse>;
}

function evidenceErrorKind(
  status: number,
): EvidenceApiError["kind"] {
  if (status === 401 || status === 403) return "unauthorized";
  if (status === 404) return "not-found";
  if (status === 503) return "unavailable";
  return "technical";
}

/**
 * Çözüm formunda seçilebilir kanıtlar: kayıtlı kanıtlar ve kural
 * çalıştırmasının sonuç/log adayları.
 */
export async function fetchIssueEvidence(
  issueId: string,
  signal?: AbortSignal,
): Promise<IssueEvidenceListApiResponse> {
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/evidence`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  if (!response.ok) throw issueApiError(response);
  return response.json() as Promise<IssueEvidenceListApiResponse>;
}

/** Bir çalıştırma adayını kalıcı kanıt kaydına dönüştürür (idempotent). */
export async function captureIssueEvidence(
  issueId: string,
  candidateKey: string,
): Promise<{
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: IssueEvidenceApiItem;
}> {
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/evidence`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ candidate_key: candidateKey }),
    },
  );
  if (!response.ok) throw issueApiError(response);
  return response.json();
}

export async function uploadIssueEvidence(
  issueId: string,
  file: File,
  label: string,
  classification: string,
  onProgress?: (percentage: number) => void,
): Promise<{
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: IssueEvidenceApiItem;
}> {
  const body = new FormData();
  body.append("file", file);
  body.append("label", label);
  body.append("evidence_type", "UPLOADED_FILE");
  body.append("classification", classification);
  body.append("idempotency_key", crypto.randomUUID());
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/v1/issues/${encodeURIComponent(issueId)}/evidence/uploads`);
    xhr.withCredentials = true;
    xhr.setRequestHeader("Accept", "application/json");
    Object.entries(stateChangingHeaders()).forEach(([name, value]) => {
      xhr.setRequestHeader(name, value);
    });
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100));
    });
    xhr.addEventListener("load", () => {
      recordCsrfProof(xhr.getResponseHeader("X-CSRF-Token"));
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
        return;
      }
      reject(new IssueApiError(
        xhr.status === 401 || xhr.status === 403 ? "unauthorized"
          : xhr.status === 409 ? "conflict"
            : xhr.status === 422 ? "validation" : "technical",
        xhr.getResponseHeader("X-Correlation-ID") ?? undefined,
      ));
    });
    xhr.addEventListener("error", () => reject(new IssueApiError("technical")));
    xhr.send(body);
  });
}

export async function downloadIssueEvidence(issueId: string, evidenceId: string): Promise<void> {
  const response = await developmentFetch(
    `/api/v1/issues/${encodeURIComponent(issueId)}/evidence/${encodeURIComponent(evidenceId)}/download`,
    { credentials: "same-origin" },
  );
  if (!response.ok) throw issueApiError(response);
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? "evidence";
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
