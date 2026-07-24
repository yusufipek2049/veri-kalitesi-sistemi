export type RuleState = "normal" | "loading" | "empty" | "error" | "unauthorized" | "long-content";

export type RuleAction =
  | "CREATE_VERSION"
  | "TEST_RULE"
  | "ACTIVATE"
  | "REQUEST_APPROVAL"
  | "DECIDE_APPROVAL"
  | "WITHDRAW_APPROVAL"
  | "PASSIVATE";

export interface RuleListItem {
  id: string;
  code: string;
  name: string;
  datasetId: string;
  dimension: string;
  status: string;
  versionId: string;
  versionNo: number;
  ruleType: string;
  criticality: string;
  createdAt: string;
  availableActions: RuleAction[];
  version: number;
  pendingApprovalRequestId?: string;
}

export interface RuleListApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  items: Array<{
    quality_rule_id: string;
    code: string;
    name: string;
    dataset_id: string;
    primary_dimension: string;
    status: string;
    rule_version_id: string;
    version_no: number;
    rule_type: string;
    criticality: string;
    created_at: string;
    available_actions: RuleAction[];
    pending_approval_request_id?: string;
  }>;
}

export const syntheticRules: RuleListItem[] = [
  { id: "rule-customer-id-required", code: "DQ_CUSTOMER_ID_REQUIRED", name: "Müşteri kimliği zorunluluğu", datasetId: "dataset-customer", dimension: "COMPLETENESS", status: "ACTIVE", versionId: "rule-version-customer-id-3", versionNo: 3, ruleType: "REQUIRED", criticality: "CRITICAL", createdAt: "2026-07-19T08:30:00Z", availableActions: ["CREATE_VERSION", "PASSIVATE"], version: 3 },
  { id: "rule-account-iban-unique", code: "DQ_ACCOUNT_IBAN_UNIQUE", name: "IBAN tekillik kontrolü", datasetId: "dataset-account", dimension: "UNIQUENESS", status: "ACTIVE", versionId: "rule-version-account-iban-2", versionNo: 2, ruleType: "UNIQUE", criticality: "HIGH", createdAt: "2026-07-18T10:15:00Z", availableActions: ["CREATE_VERSION", "PASSIVATE"], version: 2 },
  { id: "rule-risk-score-range", code: "DQ_RISK_SCORE_RANGE", name: "Risk skoru geçerlilik aralığı", datasetId: "dataset-risk", dimension: "VALIDITY", status: "REVIEW_REQUIRED", versionId: "rule-version-risk-score-4", versionNo: 4, ruleType: "RANGE", criticality: "CRITICAL", createdAt: "2026-07-21T13:45:00Z", availableActions: ["DECIDE_APPROVAL", "WITHDRAW_APPROVAL"], version: 4, pendingApprovalRequestId: "apr-risk-score-1" },
  { id: "rule-transaction-freshness", code: "DQ_TRANSACTION_FRESHNESS", name: "İşlem verisi güncelliği", datasetId: "dataset-transaction", dimension: "TIMELINESS", status: "DRAFT", versionId: "rule-version-transaction-freshness-1", versionNo: 1, ruleType: "FRESHNESS", criticality: "MEDIUM", createdAt: "2026-07-22T07:05:00Z", availableActions: ["CREATE_VERSION", "TEST_RULE", "ACTIVATE"], version: 1 },
  { id: "rule-branch-code-reference", code: "DQ_BRANCH_CODE_REFERENCE", name: "Şube kodu referans bütünlüğü", datasetId: "dataset-account", dimension: "INTEGRITY", status: "PASSIVE", versionId: "rule-version-branch-code-2", versionNo: 2, ruleType: "REFERENTIAL_INTEGRITY", criticality: "LOW", createdAt: "2026-07-17T09:00:00Z", availableActions: ["CREATE_VERSION"], version: 2 },
];

export interface RuleCreateRequest {
  code: string;
  name: string;
  dataset_id: string;
  rule_type: string;
  primary_dimension: string;
  threshold: number;
  weight: number;
  criticality: string;
  owner_user_id: string;
  parameters: Record<string, unknown>;
}

export interface RuleVersionCreateRequest {
  threshold: number;
  weight: number;
  criticality: string;
  parameters: Record<string, unknown>;
}

export interface RuleTestRequest {
  rule_version_id: string;
  limit: number;
}

export interface RuleTestResult {
  rule_test_result_id: string;
  rule_version_id: string;
  status: string;
  record_limit: number;
  checked_count: number;
  passed_count: number;
  failed_count: number;
  not_evaluated_count: number;
  success_rate: number | null;
  preview_score: number | null;
  official_score_included: boolean;
  error_class: string | null;
  message: string;
  created_at: string;
}

export interface RuleApprovalRequestPayload {
  quality_rule_id: string;
}

export interface RuleApprovalDecisionRequest {
  approval_request_id: string;
  decision: "APPROVE" | "REJECT";
  reason_code: string;
}

export interface RuleApprovalWithdrawRequest {
  approval_request_id: string;
  reason_code: string;
}

export interface RulePassivationRequest {
  quality_rule_id: string;
}

export interface RuleMutationApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: {
    quality_rule_id: string;
    code: string;
    name: string;
    dataset_id: string;
    primary_dimension: string;
    status: string;
    rule_version_id: string;
    version_no: number;
    rule_type: string;
    criticality: string;
    created_at: string;
    available_actions: RuleAction[];
  };
}

export function rulesFromApi(response: RuleListApiResponse): RuleListItem[] {
  return response.items.map((item) => ({
    id: item.quality_rule_id,
    code: item.code,
    name: item.name,
    datasetId: item.dataset_id,
    dimension: item.primary_dimension,
    status: item.status,
    versionId: item.rule_version_id,
    versionNo: item.version_no,
    ruleType: item.rule_type,
    criticality: item.criticality,
    createdAt: item.created_at,
    availableActions: item.available_actions ?? [],
    version: 0,
    pendingApprovalRequestId: item.pending_approval_request_id,
  }));
}