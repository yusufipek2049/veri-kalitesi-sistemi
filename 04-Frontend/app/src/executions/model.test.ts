import { describe, expect, it } from "vitest";
import { executionsFromApi, type ExecutionListApiResponse } from "./model";

describe("çalıştırma liste modeli", () => {
  it("API alanlarını veri-minimum ekran modeline dönüştürür", () => {
    const response: ExecutionListApiResponse = {
      api_version: "v1",
      data_origin: "synthetic-test",
      correlation_id: "correlation-execution",
      limit: 100,
      items: [{ execution_id: "execution-1", execution_type: "MANUAL", status: "PARTIAL", workload_class: "HEAVY", rule_count: 2, source_count: 1, attempt_count: 1, error_class: "QUERY_TIMEOUT", created_at: "2026-07-23T09:00:00Z", started_at: "2026-07-23T09:01:00Z", finished_at: "2026-07-23T09:31:00Z" }],
    };

    expect(executionsFromApi(response)).toEqual([{ id: "execution-1", executionType: "MANUAL", status: "PARTIAL", workloadClass: "HEAVY", ruleCount: 2, sourceCount: 1, attemptCount: 1, errorClass: "QUERY_TIMEOUT", createdAt: "2026-07-23T09:00:00Z", startedAt: "2026-07-23T09:01:00Z", finishedAt: "2026-07-23T09:31:00Z" }]);
  });
});
