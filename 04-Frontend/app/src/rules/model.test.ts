import { describe, expect, it } from "vitest";
import { rulesFromApi, type RuleListApiResponse } from "./model";

describe("kural liste modeli", () => {
  it("API alanlarını ekran modeline dönüştürür", () => {
    const response: RuleListApiResponse = {
      api_version: "v1",
      data_origin: "synthetic-test",
      correlation_id: "correlation-rule",
      items: [{ quality_rule_id: "rule-1", code: "DQ_1", name: "Kural 1", dataset_id: "dataset-1", primary_dimension: "VALIDITY", status: "ACTIVE", rule_version_id: "version-2", version_no: 2, rule_type: "RANGE", criticality: "HIGH", created_at: "2026-07-22T09:00:00Z" }],
    };

    expect(rulesFromApi(response)).toEqual([{ id: "rule-1", code: "DQ_1", name: "Kural 1", datasetId: "dataset-1", dimension: "VALIDITY", status: "ACTIVE", versionId: "version-2", versionNo: 2, ruleType: "RANGE", criticality: "HIGH", createdAt: "2026-07-22T09:00:00Z" }]);
  });
});
