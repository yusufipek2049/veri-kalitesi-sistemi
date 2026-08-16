export type IssueState = "normal" | "loading" | "empty" | "error" | "unauthorized" | "long-content";
type IssueAction = "START_INVESTIGATION" | "REASSIGN" | "RESOLVE" | "VERIFY" | "CLOSE" | "CREATE_ISSUE";
export type IssuePriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface IssueAssigneeOption {
  userId: string;
  displayName: string;
}

export interface IssueListItem {
  id: string;
  issueNo: string;
  title: string;
  sourceEventType: string;
  triggerType: string;
  scopeType: string;
  scopeId: string;
  scopeDisplayName: string | null;
  scopeParentName: string | null;
  status: string;
  priority: IssuePriority;
  occurrenceCount: number;
  version: number;
  sourceExecutionId: string | null;
  sourceRuleVersionId: string | null;
  availableActions: IssueAction[];
  createdAt: string;
  updatedAt: string;
  lastSeenAt: string;
}

export interface IssueListApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  limit: number;
  items: Array<{
    issue_id: string;
    issue_no: string;
    title: string;
    source_event_type: string;
    trigger_type: string;
    scope_type: string;
    scope_id: string;
    scope_display_name: string | null;
    scope_parent_name: string | null;
    status: string;
    priority: IssuePriority;
    occurrence_count: number;
    version: number;
    source_execution_id: string | null;
    source_rule_version_id: string | null;
    available_actions: IssueAction[];
    created_at: string;
    updated_at: string;
    last_seen_at: string;
  }>;
  available_actions: IssueAction[];
}

export interface IssueAssigneeOptionsApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  items: Array<{
    user_id: string;
    display_name: string;
  }>;
}

export interface IssueCreateInput {
  title: string;
  scopeType: "DATASET" | "SOURCE";
  scopeId: string;
  priority: IssuePriority;
}

export const syntheticIssues: IssueListItem[] = [
  { id: "issue-critical-customer", issueNo: "DQI-2026-0018", title: "Kritik müşteri verisi kalite sorunu", sourceEventType: "QUALITY", triggerType: "CRITICAL_RULE_FAILURE", scopeType: "DATASET", scopeId: "dataset-customer", scopeDisplayName: "public.customers", scopeParentName: "Production DB", status: "NEW", priority: "CRITICAL", occurrenceCount: 1, version: 1, sourceExecutionId: "exec-001", sourceRuleVersionId: "rv-001", availableActions: [], createdAt: "2026-07-23T08:10:00Z", updatedAt: "2026-07-23T08:10:00Z", lastSeenAt: "2026-07-23T08:10:00Z" },
  { id: "issue-technical-risk", issueNo: "DQI-2026-0017", title: "Risk verimartışı teknik hatası", sourceEventType: "TECHNICAL", triggerType: "TECHNICAL_ERROR", scopeType: "SOURCE", scopeId: "source-risk-mart", scopeDisplayName: "Risk Mart DB", scopeParentName: null, status: "ASSIGNED", priority: "HIGH", occurrenceCount: 3, version: 1, sourceExecutionId: null, sourceRuleVersionId: null, availableActions: ["START_INVESTIGATION", "REASSIGN"], createdAt: "2026-07-22T15:00:00Z", updatedAt: "2026-07-23T07:40:00Z", lastSeenAt: "2026-07-23T07:40:00Z" },
  { id: "issue-account-investigation", issueNo: "DQI-2026-0016", title: "Hesap verisi eşleşme sorunu", sourceEventType: "QUALITY", triggerType: "QUALITY_THRESHOLD", scopeType: "DATASET", scopeId: "dataset-account", scopeDisplayName: "public.accounts", scopeParentName: "Production DB", status: "INVESTIGATING", priority: "HIGH", occurrenceCount: 2, version: 2, sourceExecutionId: "exec-002", sourceRuleVersionId: "rv-002", availableActions: ["REASSIGN", "RESOLVE"], createdAt: "2026-07-21T10:30:00Z", updatedAt: "2026-07-22T16:20:00Z", lastSeenAt: "2026-07-22T16:20:00Z" },
  { id: "issue-transaction-waiting", issueNo: "DQI-2026-0015", title: "İşlem verisi çözüm bekliyor", sourceEventType: "QUALITY", triggerType: "QUALITY_THRESHOLD", scopeType: "DATASET", scopeId: "dataset-transaction", scopeDisplayName: "public.transactions", scopeParentName: "Production DB", status: "WAITING_FOR_RESOLUTION", priority: "MEDIUM", occurrenceCount: 4, version: 3, sourceExecutionId: "exec-003", sourceRuleVersionId: "rv-003", availableActions: ["RESOLVE"], createdAt: "2026-07-19T09:00:00Z", updatedAt: "2026-07-22T11:45:00Z", lastSeenAt: "2026-07-22T11:45:00Z" },
  { id: "issue-risk-resolved", issueNo: "DQI-2026-0014", title: "Risk verisi kritik kontrol", sourceEventType: "QUALITY", triggerType: "CRITICAL_RULE_FAILURE", scopeType: "DATASET", scopeId: "dataset-risk", scopeDisplayName: "public.risk_scores", scopeParentName: "Risk Mart DB", status: "RESOLVED", priority: "CRITICAL", occurrenceCount: 1, version: 4, sourceExecutionId: "exec-004", sourceRuleVersionId: "rv-004", availableActions: [], createdAt: "2026-07-18T13:15:00Z", updatedAt: "2026-07-21T14:10:00Z", lastSeenAt: "2026-07-18T13:15:00Z" },
  { id: "issue-customer-verified", issueNo: "DQI-2026-0013", title: "Müşteri verisi doğrulandı", sourceEventType: "QUALITY", triggerType: "QUALITY_THRESHOLD", scopeType: "DATASET", scopeId: "dataset-customer", scopeDisplayName: "public.customers", scopeParentName: "Production DB", status: "VERIFIED", priority: "MEDIUM", occurrenceCount: 1, version: 5, sourceExecutionId: "exec-005", sourceRuleVersionId: "rv-005", availableActions: [], createdAt: "2026-07-17T12:00:00Z", updatedAt: "2026-07-20T15:30:00Z", lastSeenAt: "2026-07-17T12:00:00Z" },
  { id: "issue-account-closed", issueNo: "DQI-2026-0012", title: "Hesap verisi kapatıldı", sourceEventType: "QUALITY", triggerType: "QUALITY_THRESHOLD", scopeType: "DATASET", scopeId: "dataset-account", scopeDisplayName: "public.accounts", scopeParentName: "Production DB", status: "CLOSED", priority: "LOW", occurrenceCount: 1, version: 6, sourceExecutionId: "exec-006", sourceRuleVersionId: "rv-006", availableActions: [], createdAt: "2026-07-15T08:00:00Z", updatedAt: "2026-07-19T10:00:00Z", lastSeenAt: "2026-07-15T08:00:00Z" },
  { id: "issue-source-cancelled", issueNo: "DQI-2026-0011", title: "Müşteri dosya kaynağı iptal", sourceEventType: "TECHNICAL", triggerType: "TECHNICAL_ERROR", scopeType: "SOURCE", scopeId: "source-customer-file", scopeDisplayName: "Customer File Store", scopeParentName: null, status: "CANCELLED", priority: "LOW", occurrenceCount: 1, version: 2, sourceExecutionId: null, sourceRuleVersionId: null, availableActions: [], createdAt: "2026-07-14T09:00:00Z", updatedAt: "2026-07-18T09:00:00Z", lastSeenAt: "2026-07-14T09:00:00Z" },
];

export function issueFromApiItem(
  item: IssueListApiResponse["items"][number],
): IssueListItem {
  return {
    id: item.issue_id,
    issueNo: item.issue_no,
    title: item.title,
    sourceEventType: item.source_event_type,
    triggerType: item.trigger_type,
    scopeType: item.scope_type,
    scopeId: item.scope_id,
    scopeDisplayName: item.scope_display_name ?? null,
    scopeParentName: item.scope_parent_name ?? null,
    status: item.status,
    priority: item.priority,
    occurrenceCount: item.occurrence_count,
    version: item.version,
    sourceExecutionId: item.source_execution_id ?? null,
    sourceRuleVersionId: item.source_rule_version_id ?? null,
    availableActions: item.available_actions,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
    lastSeenAt: item.last_seen_at,
  };
}

export function issuesFromApi(response: IssueListApiResponse): IssueListItem[] {
  return response.items.map(issueFromApiItem);
}

export function assigneeOptionsFromApi(
  response: IssueAssigneeOptionsApiResponse
): IssueAssigneeOption[] {
  return response.items.map((item) => ({
    userId: item.user_id,
    displayName: item.display_name,
  }));
}

// ---------------------------------------------------------------------------
// Evidence investigation (lineage snapshot + governance projection)
// ---------------------------------------------------------------------------

export type EvidenceSourceClass =
  | "Observed"
  | "Calculated"
  | "Estimated"
  | "Unknown";

const VALID_SOURCE_CLASSES: ReadonlySet<EvidenceSourceClass> = new Set([
  "Observed",
  "Calculated",
  "Estimated",
  "Unknown",
]);

function normalizeSourceClass(raw: string): EvidenceSourceClass {
  const normalized = raw.trim() as EvidenceSourceClass;
  return VALID_SOURCE_CLASSES.has(normalized) ? normalized : "Unknown";
}

// ---------------------------------------------------------------------------
// Investigation evidence (BE-04 — salt okunur ihlal inceleme kaniti)
// ---------------------------------------------------------------------------

export interface EvidenceComponent {
  source: EvidenceSourceClass;
  value: Record<string, unknown> | Array<unknown> | string | null;
  references: string[];
}

export interface InvestigationEvidence {
  issueId: string;
  ruleDescription: EvidenceComponent;
  expectedSummary: EvidenceComponent;
  actualSummary: EvidenceComponent;
  maskedSamples: EvidenceComponent;
  similarHistory: EvidenceComponent;
  recommendation: EvidenceComponent;
  ruleVersionId: string | null;
  irVersion: string | null;
  evidenceFingerprint: string | null;
  evidenceQueryReference: string | null;
  evidencePlanReference: string | null;
  authorizationPolicyVersion: string;
}

export interface InvestigationEvidenceApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  issue_id: string;
  rule_description: {
    source: string;
    value: Record<string, unknown> | Array<unknown> | string | null;
    references: readonly string[];
  };
  expected_summary: {
    source: string;
    value: Record<string, unknown> | Array<unknown> | string | null;
    references: readonly string[];
  };
  actual_summary: {
    source: string;
    value: Record<string, unknown> | Array<unknown> | string | null;
    references: readonly string[];
  };
  masked_samples: {
    source: string;
    value: Record<string, unknown> | Array<unknown> | string | null;
    references: readonly string[];
  };
  similar_history: {
    source: string;
    value: Record<string, unknown> | Array<unknown> | string | null;
    references: readonly string[];
  };
  recommendation: {
    source: string;
    value: Record<string, unknown> | Array<unknown> | string | null;
    references: readonly string[];
  };
  rule_version_id: string | null;
  ir_version: string | null;
  evidence_fingerprint: string | null;
  evidence_query_reference: string | null;
  evidence_plan_reference: string | null;
  authorization_policy_version: string;
}

function evidenceComponentFromApi(component: {
  source: string;
  value: Record<string, unknown> | Array<unknown> | string | null;
  references: readonly string[];
}): EvidenceComponent {
  return {
    source: normalizeSourceClass(component.source),
    value: component.value,
    references: [...component.references],
  };
}

export function investigationEvidenceFromApi(
  response: InvestigationEvidenceApiResponse,
): InvestigationEvidence {
  return {
    issueId: response.issue_id,
    ruleDescription: evidenceComponentFromApi(response.rule_description),
    expectedSummary: evidenceComponentFromApi(response.expected_summary),
    actualSummary: evidenceComponentFromApi(response.actual_summary),
    maskedSamples: evidenceComponentFromApi(response.masked_samples),
    similarHistory: evidenceComponentFromApi(response.similar_history),
    recommendation: evidenceComponentFromApi(response.recommendation),
    ruleVersionId: response.rule_version_id,
    irVersion: response.ir_version,
    evidenceFingerprint: response.evidence_fingerprint,
    evidenceQueryReference: response.evidence_query_reference,
    evidencePlanReference: response.evidence_plan_reference,
    authorizationPolicyVersion: response.authorization_policy_version,
  };
}

export function evidenceComponentValueText(
  component: EvidenceComponent,
): string {
  if (component.value === null || component.value === undefined) return "";
  if (typeof component.value === "string") return component.value;
  if (Array.isArray(component.value)) {
    return component.value.map((item) => String(item)).join("\n");
  }
  try {
    return JSON.stringify(component.value, null, 2);
  } catch {
    return String(component.value);
  }
}

// ---------------------------------------------------------------------------
// Çözüm kanıtı defteri
//
// Çözüm formu artık serbest metin UUID istemez: kanıtlar kural çalıştırmasının
// sonuç ve loglarından türetilir, seçilen aday kalıcı bir kanıt kaydına dönüşür
// ve çözüm o kaydın kimliğine bağlanır.
// ---------------------------------------------------------------------------

export type IssueEvidenceKind =
  | "EXECUTION_RESULT"
  | "EXECUTION_LOG"
  | "LEGACY_REFERENCE"
  | "UPLOADED_FILE";

export interface IssueEvidenceRecord {
  evidenceId: string;
  issueId: string;
  kind: IssueEvidenceKind;
  label: string;
  executionId: string;
  ruleVersionId: string | null;
  evaluatedCount: number | null;
  failedCount: number | null;
  measurementStatus: string | null;
  fingerprint: string | null;
  queryReference: string | null;
  planReference: string | null;
  contentDigest: string;
  observedAt: string;
  capturedAt: string;
  capturedBy: string;
  originalFilename?: string | null;
  detectedMediaType?: string | null;
  byteSize?: number | null;
  scanStatus?: "PENDING_SCAN" | "AVAILABLE" | "REJECTED" | "SCAN_FAILED" | null;
  scanReasonCode?: string | null;
  classification?: string | null;
}

export interface IssueEvidenceCandidate {
  candidateKey: string;
  kind: IssueEvidenceKind;
  label: string;
  executionId: string;
  ruleVersionId: string | null;
  evaluatedCount: number | null;
  failedCount: number | null;
  measurementStatus: string | null;
  observedAt: string;
}

export interface IssueEvidenceApiItem {
  evidence_id: string;
  issue_id: string;
  kind: string;
  label: string;
  execution_id: string;
  rule_version_id: string | null;
  evaluated_count: number | null;
  failed_count: number | null;
  measurement_status: string | null;
  fingerprint: string | null;
  query_reference: string | null;
  plan_reference: string | null;
  content_digest: string;
  observed_at: string;
  captured_at: string;
  captured_by: string;
  original_filename?: string | null;
  detected_media_type?: string | null;
  byte_size?: number | null;
  scan_status?: "PENDING_SCAN" | "AVAILABLE" | "REJECTED" | "SCAN_FAILED" | null;
  scan_reason_code?: string | null;
  classification?: string | null;
}

export interface IssueEvidenceApiCandidate {
  candidate_key: string;
  kind: string;
  label: string;
  execution_id: string;
  rule_version_id: string | null;
  evaluated_count: number | null;
  failed_count: number | null;
  measurement_status: string | null;
  observed_at: string;
}

export interface IssueEvidenceListApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  issue_id: string;
  items: readonly IssueEvidenceApiItem[];
  candidates: readonly IssueEvidenceApiCandidate[];
}

const EVIDENCE_KINDS = new Set<IssueEvidenceKind>([
  "EXECUTION_RESULT",
  "EXECUTION_LOG",
  "LEGACY_REFERENCE",
  "UPLOADED_FILE",
]);

function normalizeEvidenceKind(raw: string): IssueEvidenceKind {
  const normalized = raw.trim() as IssueEvidenceKind;
  return EVIDENCE_KINDS.has(normalized) ? normalized : "LEGACY_REFERENCE";
}

export function issueEvidenceRecordFromApi(
  item: IssueEvidenceApiItem,
): IssueEvidenceRecord {
  return {
    evidenceId: item.evidence_id,
    issueId: item.issue_id,
    kind: normalizeEvidenceKind(item.kind),
    label: item.label,
    executionId: item.execution_id,
    ruleVersionId: item.rule_version_id,
    evaluatedCount: item.evaluated_count,
    failedCount: item.failed_count,
    measurementStatus: item.measurement_status,
    fingerprint: item.fingerprint,
    queryReference: item.query_reference,
    planReference: item.plan_reference,
    contentDigest: item.content_digest,
    observedAt: item.observed_at,
    capturedAt: item.captured_at,
    capturedBy: item.captured_by,
    originalFilename: item.original_filename ?? null,
    detectedMediaType: item.detected_media_type ?? null,
    byteSize: item.byte_size ?? null,
    scanStatus: item.scan_status ?? null,
    scanReasonCode: item.scan_reason_code ?? null,
    classification: item.classification ?? null,
  };
}

export function issueEvidenceCandidateFromApi(
  item: IssueEvidenceApiCandidate,
): IssueEvidenceCandidate {
  return {
    candidateKey: item.candidate_key,
    kind: normalizeEvidenceKind(item.kind),
    label: item.label,
    executionId: item.execution_id,
    ruleVersionId: item.rule_version_id,
    evaluatedCount: item.evaluated_count,
    failedCount: item.failed_count,
    measurementStatus: item.measurement_status,
    observedAt: item.observed_at,
  };
}

/** Kanıt seçeneği: kayıtlı kanıt veya henüz kaydedilmemiş aday. */
export type IssueEvidenceOption =
  | { kind: "record"; value: string; label: string; record: IssueEvidenceRecord }
  | {
      kind: "candidate";
      value: string;
      label: string;
      candidate: IssueEvidenceCandidate;
    };

export function issueEvidenceOptions(
  records: readonly IssueEvidenceRecord[],
  candidates: readonly IssueEvidenceCandidate[],
): IssueEvidenceOption[] {
  return [
    ...records.filter((record) => record.kind !== "UPLOADED_FILE"
      || record.scanStatus === "AVAILABLE").map<IssueEvidenceOption>((record) => ({
      kind: "record",
      value: `record:${record.evidenceId}`,
      label: record.label,
      record,
    })),
    ...candidates.map<IssueEvidenceOption>((candidate) => ({
      kind: "candidate",
      value: `candidate:${candidate.candidateKey}`,
      label: candidate.label,
      candidate,
    })),
  ];
}
