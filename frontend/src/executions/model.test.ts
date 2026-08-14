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
        datasets: [{ dataset_id: "ds-tx", name: "transactions", namespace: "public", source_id: "src-core", source_name: "Core DB" }],
        schedule_id: null,
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
      datasets: [{ datasetId: "ds-tx", name: "transactions", namespace: "public", sourceId: "src-core", sourceName: "Core DB" }],
      scheduleId: undefined,
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
        datasets: [],
        schedule_id: null,
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
      execution: {
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
        datasets: [{ dataset_id: "ds-acct", name: "accounts", namespace: "public", source_id: "src-core", source_name: "Core DB" }],
        schedule_id: "schedule-daily",
        created_at: "2026-07-23T09:00:00Z",
        started_at: "2026-07-23T09:01:00Z",
        finished_at: "2026-07-23T09:10:00Z",
      },
      rule_results: [{
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
    expect(detail.item.datasets).toHaveLength(1);
    expect(detail.item.datasets[0].name).toBe("accounts");
    expect(detail.item.scheduleId).toBe("schedule-daily");
    expect(detail.results).toHaveLength(1);
    expect(detail.results[0].ruleVersionId).toBe("rv-1");
    expect(detail.results[0].passedCount).toBe(950);
    expect(detail.jobInfo).toBeNull();
  });

  it("job bilgisini detay modeline aktarır", () => {
    const response: ExecutionDetailApiResponse = {
      api_version: "v1",
      data_origin: "backend",
      correlation_id: "correlation-job",
      execution: {
        execution_id: "execution-job",
        execution_type: "MANUAL",
        execution_mode: "OFFICIAL",
        status: "RUNNING",
        workload_class: "LIGHT",
        rule_count: 1,
        source_count: 1,
        attempt_count: 2,
        error_class: null,
        progress_percent: 50,
        blocked_reason_code: null,
        available_actions: ["cancel"],
        datasets: [],
        schedule_id: null,
        created_at: "2026-07-23T09:00:00Z",
        started_at: "2026-07-23T09:01:00Z",
        finished_at: null,
      },
      rule_results: [],
      job_info: {
        job_id: "execution-job",
        status: "RUNNING",
        queue_position: null,
        worker_id: "worker-a",
        leased_until: "2026-07-23T09:06:00Z",
        attempt_count: 2,
        last_error_class: null,
        completed_at: null,
        completion_outcome: null,
      },
    };

    const detail = executionDetailFromApi(response);
    expect(detail.jobInfo).not.toBeNull();
    expect(detail.jobInfo!.jobId).toBe("execution-job");
    expect(detail.jobInfo!.status).toBe("RUNNING");
    expect(detail.jobInfo!.workerId).toBe("worker-a");
    expect(detail.jobInfo!.attemptCount).toBe(2);
  });
});
