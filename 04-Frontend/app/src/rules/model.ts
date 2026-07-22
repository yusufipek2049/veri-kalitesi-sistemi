export type RuleState = "normal" | "loading" | "empty" | "error" | "unauthorized" | "long-content";

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
  }>;
}

export const syntheticRules: RuleListItem[] = [
  { id: "rule-customer-id-required", code: "DQ_CUSTOMER_ID_REQUIRED", name: "Müşteri kimliği zorunluluğu", datasetId: "dataset-customer", dimension: "COMPLETENESS", status: "ACTIVE", versionId: "rule-version-customer-id-3", versionNo: 3, ruleType: "REQUIRED", criticality: "CRITICAL", createdAt: "2026-07-19T08:30:00Z" },
  { id: "rule-account-iban-unique", code: "DQ_ACCOUNT_IBAN_UNIQUE", name: "IBAN tekillik kontrolü", datasetId: "dataset-account", dimension: "UNIQUENESS", status: "ACTIVE", versionId: "rule-version-account-iban-2", versionNo: 2, ruleType: "UNIQUE", criticality: "HIGH", createdAt: "2026-07-18T10:15:00Z" },
  { id: "rule-risk-score-range", code: "DQ_RISK_SCORE_RANGE", name: "Risk skoru geçerlilik aralığı", datasetId: "dataset-risk", dimension: "VALIDITY", status: "REVIEW_REQUIRED", versionId: "rule-version-risk-score-4", versionNo: 4, ruleType: "RANGE", criticality: "CRITICAL", createdAt: "2026-07-21T13:45:00Z" },
  { id: "rule-transaction-freshness", code: "DQ_TRANSACTION_FRESHNESS", name: "İşlem verisi güncelliği", datasetId: "dataset-transaction", dimension: "TIMELINESS", status: "DRAFT", versionId: "rule-version-transaction-freshness-1", versionNo: 1, ruleType: "FRESHNESS", criticality: "MEDIUM", createdAt: "2026-07-22T07:05:00Z" },
  { id: "rule-branch-code-reference", code: "DQ_BRANCH_CODE_REFERENCE", name: "Şube kodu referans bütünlüğü", datasetId: "dataset-account", dimension: "INTEGRITY", status: "PASSIVE", versionId: "rule-version-branch-code-2", versionNo: 2, ruleType: "REFERENTIAL_INTEGRITY", criticality: "LOW", createdAt: "2026-07-17T09:00:00Z" },
];

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
  }));
}
