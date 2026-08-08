import { describe, expect, it } from "vitest";
import {
  executionDetailFromApi,
  executionsFromApi,
  type ExecutionDetailApiResponse,
  type ExecutionListApiResponse,
} from "./model";

describe("çalıştırma liste modeli", () => {
  it("API alanlarını veri-minimum ekran modeline dönüştürür", () => {
    const response: ExecutionListApiResponse = {
      api_version: "v1",
      data_origin: "synthetic-test",
      correlation_id: "correlation-execution",
      limit: 100,
      items: [{
        execution_id: "execution-1",
        execution_type: "MANUAL",
        execution_mode: "SHADOW",
        status: "PARTIAL",
        workload_class: "HEAVY",
        rule_count: 2,
        source_count: 1,
        attempt_count: 1,
        error_class: "QUERY_TIMEOUT",
        progress_percent: 78,
        blocked_reason_code: null,
        available_actions: [],
        created_at: "2026-07-23T09:00:00Z",
        started_at: "2026-07-23T09:01:00Z",
        finished_at: "2026-07-23T09:31:00Z",
      }],
    };

    expect(executionsFromApi(response)).toEqual([{
      id: "execution-1",
      executionType: "MANUAL",
      executionMode: "SHADOW",
      status: "PARTIAL",
      workloadClass: "HEAVY",
      ruleCount: 2,
      sourceCount: 1,
      attemptCount: 1,
      errorClass: "QUERY_TIMEOUT",
      progressPercent: 78,
      blockedReasonCode: undefined,
      availableActions: [],
      createdAt: "2026-07-23T09:00:00Z",
      startedAt: "2026-07-23T09:01:00Z",
      finishedAt: "2026-07-23T09:31:00Z",
    }]);
  });

  it("blocked_reason_code ve available_actions alanlarını doğru aktarır", () => {
    const response: ExecutionListApiResponse = {
      api_version: "v1",
      data_origin: "synthetic-test",
      correlation_id: "correlation-blocked",
      limit: 100,
      items: [{
        execution_id: "execution-blocked",
        execution_type: "MANUAL",
        status: "BLOCKED",
        workload_class: "HEAVY",
        rule_count: 1,
        source_count: 1,
        attempt_count: 0,
        error_class: null,
        progress_percent: 0,
        blocked_reason_code: "SOURCE_LOCKED",
        available_actions: ["cancel"],
        created_at: "2026-07-23T09:00:00Z",
        started_at: null,
        finished_at: null,
      }],
    };

    const result = executionsFromApi(response);
    expect(result[0].blockedReasonCode).toBe("SOURCE_LOCKED");
    expect(result[0].availableActions).toEqual(["cancel"]);
  });
});

describe("çalıştırma detay modeli", () => {
  it("detay yanıtını ekran modeline dönüştürür", () => {
    const response: ExecutionDetailApiResponse = {
      api_version: "v1",
      data_origin: "backend",
      correlation_id: "correlation-detail",
      item: {
        execution_id: "execution-detail",
        execution_type: "MANUAL",
        execution_mode: "OFFICIAL",
        status: "SUCCESS",
        workload_class: "LIGHT",
        rule_count: 1,
        source_count: 1,
        attempt_count: 1,
        error_class: null,
        progress_percent: 100,
        blocked_reason_code: null,
        available_actions: [],
        created_at: "2026-07-23T09:00:00Z",
        started_at: "2026-07-23T09:01:00Z",
        finished_at: "2026-07-23T09:10:00Z",
      },
      results: [{
        rule_version_id: "rv-1",
        population_count: 1000,
        passed_count: 950,
        failed_count: 50,
        evaluated_count: 1000,
        measurement_status: "PASSED",
      }],
    };

    const detail = executionDetailFromApi(response);
    expect(detail.item.id).toBe("execution-detail");
    expect(detail.item.progressPercent).toBe(100);
    expect(detail.results).toHaveLength(1);
    expect(detail.results[0].ruleVersionId).toBe("rv-1");
    expect(detail.results[0].passedCount).toBe(950);
  });
});
