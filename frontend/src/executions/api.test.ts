import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ExecutionApiError,
  cancelExecution,
  fetchExecutionDetail,
  fetchExecutions,
  startExecution,
} from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("çalıştırma liste API istemcisi", () => {
  it("başarılı yanıtı döndürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ api_version: "v1", data_origin: "test", correlation_id: "c-1", limit: 100, items: [] }), { status: 200 })));
    await expect(fetchExecutions()).resolves.toMatchObject({ correlation_id: "c-1", items: [] });
  });

  it("yetki reddini forbidden hata türüyle taşır", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 403, headers: { "X-Correlation-ID": "c-denied" } })));
    await expect(fetchExecutions()).rejects.toEqual(new ExecutionApiError("forbidden", "c-denied"));
  });

  it("yetkisiz erişimi unauthorized hata türüyle taşır", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 401, headers: { "X-Correlation-ID": "c-auth" } })));
    await expect(fetchExecutions()).rejects.toEqual(new ExecutionApiError("unauthorized", "c-auth"));
  });

  it("teknik hatayı güvenli hata türüne dönüştürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 503, headers: { "X-Correlation-ID": "c-error" } })));
    await expect(fetchExecutions()).rejects.toEqual(new ExecutionApiError("technical", "c-error"));
  });

  it("çakışma hatasını conflict türüne dönüştürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 409, headers: { "X-Correlation-ID": "c-conflict" } })));
    await expect(fetchExecutions()).rejects.toEqual(new ExecutionApiError("conflict", "c-conflict"));
  });
});

describe("çalıştırma detay API istemcisi", () => {
  it("detay yanıtını döndürür", async () => {
    const body = {
      api_version: "v1",
      data_origin: "test",
      correlation_id: "c-detail",
      item: {
        execution_id: "e-1", execution_type: "MANUAL", status: "SUCCESS",
        workload_class: "LIGHT", rule_count: 1, source_count: 1, attempt_count: 1,
        error_class: null, progress_percent: 100, blocked_reason_code: null,
        available_actions: [], created_at: "2026-07-23T09:00:00Z",
        started_at: "2026-07-23T09:01:00Z", finished_at: "2026-07-23T09:10:00Z",
      },
      results: [],
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 200 })));
    const result = await fetchExecutionDetail("e-1");
    expect(result.correlation_id).toBe("c-detail");
    expect(result.item.execution_id).toBe("e-1");
  });

  it("bulunamadı hatasını not_found türüne dönüştürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 404, headers: { "X-Correlation-ID": "c-nf" } })));
    await expect(fetchExecutionDetail("missing")).rejects.toEqual(new ExecutionApiError("not_found", "c-nf"));
  });
});

describe("çalıştırma başlatma API istemcisi", () => {
  it("başarılı başlatma yanıtını döndürür", async () => {
    const item = {
      execution_id: "e-new", execution_type: "MANUAL", status: "QUEUED",
      workload_class: "LIGHT", rule_count: 1, source_count: 1, attempt_count: 0,
      error_class: null, progress_percent: 0, blocked_reason_code: null,
      available_actions: ["cancel"], created_at: "2026-07-23T09:00:00Z",
      started_at: null, finished_at: null,
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ item }), { status: 201 })));
    const result = await startExecution({
      rule_version_ids: ["rv-1"],
      source_ids: ["src-1"],
      idempotency_key: "idem-1",
      execution_mode: "OFFICIAL",
    });
    expect(result.execution_id).toBe("e-new");
  });
});

describe("çalıştırma iptal API istemcisi", () => {
  it("başarılı iptal yanıtını döndürür", async () => {
    const item = {
      execution_id: "e-cancel", execution_type: "MANUAL", status: "CANCELLED",
      workload_class: "LIGHT", rule_count: 1, source_count: 1, attempt_count: 0,
      error_class: null, progress_percent: 0, blocked_reason_code: null,
      available_actions: [], created_at: "2026-07-23T09:00:00Z",
      started_at: null, finished_at: "2026-07-23T09:05:00Z",
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ item }), { status: 200 })));
    const result = await cancelExecution("e-cancel", { reason: "user request" });
    expect(result.execution_id).toBe("e-cancel");
    expect(result.status).toBe("CANCELLED");
  });
});
