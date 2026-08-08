import { describe, expect, it } from "vitest";
import {
  driftJudgmentFromApi,
  snapshotDetailFromApi,
  snapshotListItemFromApi,
  syntheticDriftJudgment,
  syntheticSnapshotDetail,
  syntheticSnapshots,
  type DriftJudgmentApiResponse,
  type ProfileSnapshotDetailApiResponse,
  type ProfileSnapshotListApiResponse,
} from "./model";

describe("profiling/model", () => {
  describe("snapshotListItemFromApi", () => {
    it("converts API response to domain model", () => {
      const apiItem: ProfileSnapshotListApiResponse["items"][0] = {
        profile_id: "p1",
        dataset_id: "ds1",
        execution_id: "e1",
        method: "FULL",
        status: "COMPLETED",
        sample_ratio: 1.0,
        duration_ms: 100,
        started_at: "2026-08-03T10:00:00Z",
        finished_at: "2026-08-03T10:00:01Z",
      };
      const result = snapshotListItemFromApi(apiItem);
      expect(result.profileId).toBe("p1");
      expect(result.datasetId).toBe("ds1");
      expect(result.method).toBe("FULL");
      expect(result.status).toBe("COMPLETED");
    });
  });

  describe("snapshotDetailFromApi", () => {
    it("converts API response to domain model with metrics", () => {
      const apiResponse: ProfileSnapshotDetailApiResponse = {
        api_version: "v1",
        data_origin: "test",
        correlation_id: "c1",
        profile_id: "p1",
        dataset_id: "ds1",
        execution_id: "e1",
        method: "FULL",
        status: "COMPLETED",
        sample_ratio: 1.0,
        duration_ms: 100,
        metrics: { row_count: 1000, profile_contract: { version: "v1" } },
        started_at: "2026-08-03T10:00:00Z",
        finished_at: "2026-08-03T10:00:01Z",
      };
      const result = snapshotDetailFromApi(apiResponse);
      expect(result.profileId).toBe("p1");
      expect(result.metrics).toEqual({ row_count: 1000, profile_contract: { version: "v1" } });
    });
  });

  describe("driftJudgmentFromApi", () => {
    it("converts API response to domain model", () => {
      const apiResponse: DriftJudgmentApiResponse = {
        api_version: "v1",
        data_origin: "test",
        correlation_id: "c1",
        item: {
          comparison_id: "comp1",
          dataset_id: "ds1",
          baseline_profile_id: "p0",
          current_profile_id: "p1",
          policy_version: "POLICY_V1",
          status: "COMPLETED",
          anomaly_candidate: false,
          result: { signals: [{ kind: "VOLUME_CHANGE", breached: false, result_kind: "NOMINAL" }] },
          message: "No drift",
          created_at: "2026-08-03T10:05:00Z",
        },
      };
      const result = driftJudgmentFromApi(apiResponse);
      expect(result.comparisonId).toBe("comp1");
      expect(result.status).toBe("COMPLETED");
      expect(result.result.signals).toHaveLength(1);
    });

    it("handles Unknown judgment status", () => {
      const apiResponse: DriftJudgmentApiResponse = {
        api_version: "v1",
        data_origin: "test",
        correlation_id: "c1",
        item: {
          comparison_id: "comp1",
          dataset_id: "ds1",
          baseline_profile_id: "",
          current_profile_id: "p1",
          policy_version: null,
          status: "INSUFFICIENT_HISTORY",
          anomaly_candidate: null,
          result: { signals: [] },
          message: "No baseline available",
          created_at: "2026-08-03T10:05:00Z",
        },
      };
      const result = driftJudgmentFromApi(apiResponse);
      expect(result.status).toBe("INSUFFICIENT_HISTORY");
      expect(result.policyVersion).toBeNull();
    });
  });

  describe("synthetic data", () => {
    it("provides synthetic snapshots", () => {
      expect(syntheticSnapshots).toHaveLength(2);
      expect(syntheticSnapshots[0].profileId).toBe("profile-001");
    });

    it("provides synthetic snapshot detail", () => {
      expect(syntheticSnapshotDetail.profileId).toBe("profile-001");
      expect(syntheticSnapshotDetail.metrics).toHaveProperty("profile_contract");
    });

    it("provides synthetic drift judgment", () => {
      expect(syntheticDriftJudgment.status).toBe("COMPLETED");
      expect(syntheticDriftJudgment.result.signals).toHaveLength(1);
    });
  });
});
