/**
 * Yönetişim görev merkezi modelleri.
 * Backend GovernanceApprovalItem projeksiyonunun frontend karşılığıdır.
 */

export type GovernanceState = "normal" | "loading" | "empty" | "error" | "unauthorized";

export type GovernanceView = "PENDING" | "MINE" | "DECIDED" | "EXPIRED" | "ALL";

export type GovernanceDomain =
  | "QUALITY_RULE"
  | "DATA_SOURCE"
  | "DATA_OWNERSHIP"
  | "METADATA_AND_CLASSIFICATION"
  | "EXECUTION";

export interface GovernanceApprovalItem {
  approvalRequestId: string;
  domain: GovernanceDomain;
  requestType: string;
  status: string;
  objectType: string;
  objectId: string;
  objectName: string;
  scopeType: string;
  scopeId: string;
  makerActorId: string;
  checkerActorId: string | null;
  reasonCode: string | null;
  requestedAt: string;
  decidedAt: string | null;
  expiresAt: string | null;
  policyVersion: string;
  availableActions: string[];
  changeSummary: Record<string, unknown>;
}

export interface GovernanceApprovalApiItem {
  approval_request_id: string;
  domain: string;
  request_type: string;
  status: string;
  object_type: string;
  object_id: string;
  object_name: string;
  scope_type: string;
  scope_id: string;
  maker_actor_id: string;
  checker_actor_id: string | null;
  reason_code: string | null;
  requested_at: string;
  decided_at: string | null;
  expires_at: string | null;
  policy_version: string;
  available_actions?: string[];
  change_summary?: Record<string, unknown>;
}

export interface GovernanceListApiResponse {
  api_version: string;
  data_origin: string;
  correlation_id: string;
  view: string;
  items: GovernanceApprovalApiItem[];
}

export const governanceViews: GovernanceView[] = ["PENDING", "MINE", "DECIDED", "EXPIRED", "ALL"];

export const governanceViewLabels: Record<GovernanceView, string> = {
  PENDING: "Onay Bekleyenler",
  MINE: "Gönderdiklerim",
  DECIDED: "Sonuçlananlar",
  EXPIRED: "Süresi Geçenler",
  ALL: "Tüm Kararlar",
};

export const governanceRequestTypeLabels: Record<string, string> = {
  RULE_APPROVAL: "Kural Onayı",
  SOURCE_ACTIVATION: "Kaynak Aktivasyonu",
  SOURCE_DEACTIVATION: "Kaynak Deaktivasyonu",
  DATASET_OWNER_ASSIGN: "Sahip Atama",
  DATASET_OWNER_CHANGE: "Sahip Değişikliği",
  METADATA_CRITICAL_CHANGE: "Kritik Metadata Değişikliği",
  FIELD_SENSITIVITY_MARK: "Alan Hassasiyet İşareti",
  EXECUTION_MANUAL_START: "Kritik Manuel Çalıştırma",
  EXECUTION_CANCEL: "Çalıştırma İptali",
  DEAD_LETTER_REPROCESS: "Dead Letter Yeniden İşleme",
};

export const governanceStatusLabels: Record<string, string> = {
  PENDING: "Bekliyor",
  APPROVED: "Onaylandı",
  REJECTED: "Reddedildi",
  WITHDRAWN: "Geri Çekildi",
  EXPIRED: "Süresi Geçti",
  INVALIDATED: "Geçersizleştirildi",
  APPLIED: "Uygulandı",
  APPLICATION_FAILED: "Uygulama Başarısız",
};

/** Karar ve geri çekme için kontrollü gerekçe kodu seçenekleri. */
export const governanceDecisionReasonCodes: string[] = [
  "OWNERSHIP.VERIFIED",
  "OWNERSHIP.INSUFFICIENT.EVIDENCE",
  "OWNERSHIP.SCOPE.MISMATCH",
  "OWNERSHIP.POLICY.VIOLATION",
  "OWNERSHIP.CORRECTION",
  "METADATA.VERIFIED",
  "METADATA.INSUFFICIENT.EVIDENCE",
  "EXECUTION.VERIFIED",
  "EXECUTION.INSUFFICIENT.EVIDENCE",
];

/** Sahiplik talepleri için gönderim gerekçe kodları. */
export const governanceOwnershipReasonCodes: string[] = [
  "OWNERSHIP.ASSIGN",
  "OWNERSHIP.TRANSFER",
  "OWNERSHIP.CORRECTION",
];

/** Kritik metadata talepleri için gönderim gerekçe kodları. */
export const governanceMetadataReasonCodes: string[] = [
  "METADATA.CRITICALITY.CHANGE",
  "METADATA.STATUS.CHANGE",
];

/** Alan hassasiyet talepleri için gönderim gerekçe kodları. */
export const governanceFieldSensitivityReasonCodes: string[] = [
  "METADATA.SENSITIVITY.MARK",
  "METADATA.CLASSIFICATION.CHANGE",
];

/** Çalıştırma talepleri için gönderim gerekçe kodları. */
export const governanceExecutionReasonCodes: string[] = [
  "EXECUTION.MANUAL.START",
  "EXECUTION.CANCEL",
  "EXECUTION.DEAD.LETTER.REPROCESS",
];

export const governanceWithdrawReasonCodes: string[] = ["MAKER.WITHDRAWAL", "OWNERSHIP.CORRECTION"];

export const governanceActionLabels: Record<string, string> = {
  DECIDE_APPROVAL: "Onayla/Reddet",
  WITHDRAW_APPROVAL: "Geri Çek",
  APPLY: "Uygula",
};

export function governanceItemFromApi(item: GovernanceApprovalApiItem): GovernanceApprovalItem {
  const domain: GovernanceDomain =
    item.domain === "DATA_SOURCE"
      ? "DATA_SOURCE"
      : item.domain === "DATA_OWNERSHIP"
        ? "DATA_OWNERSHIP"
        : item.domain === "METADATA_AND_CLASSIFICATION"
          ? "METADATA_AND_CLASSIFICATION"
          : item.domain === "EXECUTION"
            ? "EXECUTION"
            : "QUALITY_RULE";
  return {
    approvalRequestId: item.approval_request_id,
    domain,
    requestType: item.request_type,
    status: item.status,
    objectType: item.object_type,
    objectId: item.object_id,
    objectName: item.object_name,
    scopeType: item.scope_type,
    scopeId: item.scope_id,
    makerActorId: item.maker_actor_id,
    checkerActorId: item.checker_actor_id,
    reasonCode: item.reason_code,
    requestedAt: item.requested_at,
    decidedAt: item.decided_at,
    expiresAt: item.expires_at,
    policyVersion: item.policy_version,
    availableActions: item.available_actions ?? [],
    changeSummary: item.change_summary ?? {},
  };
}

export function governanceItemsFromApi(response: GovernanceListApiResponse): GovernanceApprovalItem[] {
  return response.items.map(governanceItemFromApi);
}

/** Hedef nesnenin domain ekranına giden rotasını üretir. */
export function governanceTargetHref(item: GovernanceApprovalItem): string {
  if (item.domain === "DATA_SOURCE") return "/data-sources";
  if (item.domain === "METADATA_AND_CLASSIFICATION") return `/catalog/datasets/${item.scopeId}`;
  if (item.domain === "EXECUTION") return "/executions";
  return "/rules";
}

/** Bekleyen taleplerin kalan süresini insan okunur biçimde verir. */
export function governanceRemainingLabel(item: GovernanceApprovalItem, now: Date): string | null {
  if (item.status !== "PENDING" || !item.expiresAt) return null;
  const diffMs = new Date(item.expiresAt).getTime() - now.getTime();
  if (diffMs <= 0) return "Süresi doldu";
  const hours = Math.floor(diffMs / 3_600_000);
  if (hours >= 48) return `${Math.floor(hours / 24)} gün`;
  if (hours >= 1) return `${hours} saat`;
  return `${Math.max(1, Math.floor(diffMs / 60_000))} dakika`;
}
