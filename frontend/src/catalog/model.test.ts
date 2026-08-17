import { describe, expect, it } from "vitest";
import {
  mapCatalogDataset,
  mapCatalogField,
  mapDiscoveryScope,
  mapDiscoveryStatus,
  mapMetadataDiff,
  type CatalogDatasetListApiResponse,
  type CatalogFieldListApiResponse,
  type DiscoveryDiffApiResponse,
  type DiscoveryScopeApiResponse,
  type DiscoveryStatusApiResponse,
} from "./model";

const apiDataset: CatalogDatasetListApiResponse["items"][number] = {
  dataset_id: "ds-1",
  data_source_id: "source-1",
  namespace: "public",
  name: "accounts",
  dataset_type: "TABLE",
  status: "ACTIVE",
  criticality: "MEDIUM",
  estimated_row_count: 12000,
  field_count: 8,
  version: 3,
};

const apiField: CatalogFieldListApiResponse["items"][number] = {
  data_field_id: "f-1",
  dataset_id: "ds-1",
  name: "iban",
  native_data_type: "VARCHAR(34)",
  is_nullable: false,
  is_sensitive: true,
  classification: "PII",
  status: "ACTIVE",
  version: 1,
};

const apiDiscoveryStatus: DiscoveryStatusApiResponse = {
  api_version: "v1",
  data_origin: "test",
  correlation_id: "corr-1",
  discovery_id: 42,
  data_source_id: "source-1",
  status: "PARTIAL",
  scanned_object_count: 15,
  completed_scope: { include: ["public.*"] },
  partial_reason_code: "TIMEOUT",
  started_at: "2026-08-05T10:00:00Z",
  finished_at: "2026-08-05T10:05:00Z",
  discovery_correlation_id: "corr-discovery",
};

const apiDiff: DiscoveryDiffApiResponse = {
  api_version: "v1",
  data_origin: "test",
  correlation_id: "corr-2",
  metadata_diff_id: "diff-1",
  discovery_id: 42,
  data_source_id: "source-1",
  status: "PENDING",
  added_objects: [{ kind: "dataset", name: "new_table" }],
  changed_objects: [{ kind: "field", name: "updated_column" }],
  removed_objects: [],
  requires_rule_review: true,
};

const apiScope: DiscoveryScopeApiResponse = {
  api_version: "v1",
  data_origin: "test",
  correlation_id: "corr-3",
  data_source_id: "source-1",
  include_patterns: ["public.*"],
  exclude_patterns: ["public.temp_*"],
  page_size: 100,
  max_objects: 5000,
  timeout_seconds: 300,
  version: 2,
};

describe("catalog model mappers", () => {
  it("mapCatalogDataset maps snake_case API to camelCase domain", () => {
    const result = mapCatalogDataset(apiDataset);
    expect(result.id).toBe("ds-1");
    expect(result.dataSourceId).toBe("source-1");
    expect(result.namespace).toBe("public");
    expect(result.name).toBe("accounts");
    expect(result.datasetType).toBe("TABLE");
    expect(result.status).toBe("ACTIVE");
    expect(result.criticality).toBe("MEDIUM");
    expect(result.estimatedRowCount).toBe(12000);
    expect(result.fieldCount).toBe(8);
    expect(result.version).toBe(3);
  });

  it("mapCatalogField maps snake_case API to camelCase domain", () => {
    const result = mapCatalogField(apiField);
    expect(result.id).toBe("f-1");
    expect(result.datasetId).toBe("ds-1");
    expect(result.name).toBe("iban");
    expect(result.nativeDataType).toBe("VARCHAR(34)");
    expect(result.isNullable).toBe(false);
    expect(result.isSensitive).toBe(true);
    expect(result.classification).toBe("PII");
    expect(result.status).toBe("ACTIVE");
    expect(result.version).toBe(1);
  });

  it("mapDiscoveryStatus maps lifecycle fields including correlation_id", () => {
    const result = mapDiscoveryStatus(apiDiscoveryStatus);
    expect(result.discoveryId).toBe(42);
    expect(result.dataSourceId).toBe("source-1");
    expect(result.status).toBe("PARTIAL");
    expect(result.scannedObjectCount).toBe(15);
    expect(result.partialReasonCode).toBe("TIMEOUT");
    expect(result.correlationId).toBe("corr-discovery");
    expect(result.startedAt).toBe("2026-08-05T10:00:00Z");
    expect(result.finishedAt).toBe("2026-08-05T10:05:00Z");
  });

  it("mapDiscoveryStatus handles null optional fields", () => {
    const result = mapDiscoveryStatus({
      ...apiDiscoveryStatus,
      partial_reason_code: null,
      started_at: null,
      finished_at: null,
      discovery_correlation_id: null,
    });
    expect(result.partialReasonCode).toBeNull();
    expect(result.startedAt).toBeNull();
    expect(result.finishedAt).toBeNull();
    expect(result.correlationId).toBeNull();
  });

  it("mapMetadataDiff maps diff objects and rule review flag", () => {
    const result = mapMetadataDiff(apiDiff);
    expect(result.metadataDiffId).toBe("diff-1");
    expect(result.discoveryId).toBe(42);
    expect(result.status).toBe("PENDING");
    expect(result.addedObjects).toHaveLength(1);
    expect(result.changedObjects).toHaveLength(1);
    expect(result.removedObjects).toHaveLength(0);
    expect(result.requiresRuleReview).toBe(true);
  });

  it("mapMetadataDiff handles null diff id when no diff exists", () => {
    const result = mapMetadataDiff({ ...apiDiff, metadata_diff_id: null });
    expect(result.metadataDiffId).toBeNull();
  });

  it("mapDiscoveryScope maps scope parameters and version", () => {
    const result = mapDiscoveryScope(apiScope);
    expect(result.dataSourceId).toBe("source-1");
    expect(result.includePatterns).toEqual(["public.*"]);
    expect(result.excludePatterns).toEqual(["public.temp_*"]);
    expect(result.pageSize).toBe(100);
    expect(result.maxObjects).toBe(5000);
    expect(result.timeoutSeconds).toBe(300);
    expect(result.version).toBe(2);
  });

  it("catalog dataset status types are constrained", () => {
    const active = mapCatalogDataset({ ...apiDataset, status: "ACTIVE" });
    const inactive = mapCatalogDataset({ ...apiDataset, status: "INACTIVE" });
    expect(active.status).toBe("ACTIVE");
    expect(inactive.status).toBe("INACTIVE");
  });

  it("discovery lifecycle status covers all terminal and intermediate states", () => {
    const statuses = ["QUEUED", "RUNNING", "SUCCESS", "PARTIAL", "TECHNICAL_ERROR", "CANCELLED"] as const;
    for (const status of statuses) {
      const result = mapDiscoveryStatus({ ...apiDiscoveryStatus, status });
      expect(result.status).toBe(status);
    }
  });
});
