import { describe, expect, it } from "vitest";
import {
  governanceItemFromApi,
  governanceItemsFromApi,
  governanceRemainingLabel,
  governanceTargetHref,
  type GovernanceApprovalApiItem,
} from "./model";

function apiItem(overrides: Partial<GovernanceApprovalApiItem> = {}): GovernanceApprovalApiItem {
  return {
    approval_request_id: "apr-1",
    domain: "QUALITY_RULE",
    request_type: "RULE_APPROVAL",
    status: "PENDING",
    object_type: "QualityRule",
    object_id: "rule-a",
    object_name: "DQ_RULE_A — Kural A",
    scope_type: "DATASET",
    scope_id: "dataset-a",
    maker_actor_id: "maker-1",
    checker_actor_id: null,
    reason_code: null,
    requested_at: "2026-08-14T10:00:00Z",
    decided_at: null,
    expires_at: null,
    policy_version: "GOV_V1",
    ...overrides,
  };
}

describe("yönetişim model eşlemesi", () => {
  it("API alanlarını camelCase modele dönüştürür", () => {
    const mapped = governanceItemFromApi(apiItem());
    expect(mapped.approvalRequestId).toBe("apr-1");
    expect(mapped.domain).toBe("QUALITY_RULE");
    expect(mapped.requestType).toBe("RULE_APPROVAL");
    expect(mapped.objectName).toBe("DQ_RULE_A — Kural A");
    expect(mapped.checkerActorId).toBeNull();
  });

  it("veri kaynağı domain'ini korur", () => {
    const mapped = governanceItemFromApi(apiItem({ domain: "DATA_SOURCE", request_type: "SOURCE_ACTIVATION" }));
    expect(mapped.domain).toBe("DATA_SOURCE");
    expect(governanceTargetHref(mapped)).toBe("/data-sources");
  });

  it("kural talebini kurallar ekranına yönlendirir", () => {
    expect(governanceTargetHref(governanceItemFromApi(apiItem()))).toBe("/rules");
  });

  it("metadata domain'ini korur ve katalog ekranına yönlendirir", () => {
    const mapped = governanceItemFromApi(
      apiItem({
        domain: "METADATA_AND_CLASSIFICATION",
        request_type: "METADATA_CRITICAL_CHANGE",
        object_type: "Dataset",
      }),
    );
    expect(mapped.domain).toBe("METADATA_AND_CLASSIFICATION");
    expect(governanceTargetHref(mapped)).toBe("/catalog/datasets/dataset-a");
  });

  it("birden çok öğeyi eşler", () => {
    const response = {
      api_version: "v1",
      data_origin: "test",
      correlation_id: "c-1",
      view: "ALL",
      items: [apiItem(), apiItem({ approval_request_id: "apr-2" })],
    };
    expect(governanceItemsFromApi(response)).toHaveLength(2);
  });
});

describe("kalan süre etiketi", () => {
  const now = new Date("2026-08-14T12:00:00Z");

  it("kararlanmış talepte süre göstermez", () => {
    const item = governanceItemFromApi(apiItem({ status: "APPROVED" }));
    expect(governanceRemainingLabel(item, now)).toBeNull();
  });

  it("bekleyen talepte kalan saati gösterir", () => {
    const item = governanceItemFromApi(apiItem({ expires_at: "2026-08-14T15:00:00Z" }));
    expect(governanceRemainingLabel(item, now)).toBe("3 saat");
  });

  it("süresi dolmuş talebi işaretler", () => {
    const item = governanceItemFromApi(apiItem({ expires_at: "2026-08-14T11:00:00Z" }));
    expect(governanceRemainingLabel(item, now)).toBe("Süresi doldu");
  });
});
