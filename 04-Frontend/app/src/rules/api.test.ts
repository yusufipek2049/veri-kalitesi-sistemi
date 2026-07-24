import { afterEach, describe, expect, it, vi } from "vitest";
import {
  fetchRules,
  createRule,
  createRuleVersion,
  testRule,
  activateRule,
  requestRuleApproval,
  decideRuleApproval,
  withdrawRuleApproval,
  passivateRule,
  RuleApiError,
} from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

function mockResponse(data: unknown, status = 200, headers?: Record<string, string>) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

function stubFetch(response: Response) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
}

describe("kural liste API istemcisi", () => {
  it("başarılı yanıtı döndürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ api_version: "v1", data_origin: "test", correlation_id: "c-1", items: [] }),
      { status: 200 },
    )));
    await expect(fetchRules()).resolves.toMatchObject({ correlation_id: "c-1", items: [] });
  });

  it("yetki reddini ayrı hata türüyle taşır", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 403, headers: { "X-Correlation-ID": "c-denied" } })));
    await expect(fetchRules()).rejects.toEqual(new RuleApiError("unauthorized", "c-denied"));
  });

  it("teknik hatayı güvenli hata türüne dönüştürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 503, headers: { "X-Correlation-ID": "c-error" } })));
    await expect(fetchRules()).rejects.toEqual(new RuleApiError("technical", "c-error"));
  });

  it("CSRF proof'u GET yanıtından okur", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ api_version: "v1", data_origin: "test", correlation_id: "c-1", items: [] }),
      { status: 200, headers: { "X-CSRF-Token": "test-proof" } },
    )));
    await fetchRules();
    // CSRF token stored internally — next mutation call should use it
    stubFetch(mockResponse({ api_version: "v1", data_origin: "test", correlation_id: "c-2", item: {} }, 201));
    await expect(createRule({
      code: "TEST", name: "Test", dataset_id: "ds-1", rule_type: "REQUIRED",
      primary_dimension: "COMPLETENESS", threshold: 100, weight: 1, criticality: "MEDIUM", owner_user_id: "user-1", parameters: {},
    })).resolves.toBeDefined();
  });
});

describe("kural mutasyon API istemcileri", () => {
  function setUpCsrf() {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ api_version: "v1", data_origin: "test", correlation_id: "c-init", items: [] }),
      { status: 200, headers: { "X-CSRF-Token": "test-proof" } },
    )));
    return fetchRules();
  }

  describe("createRule", () => {
    it("başarılı oluşturma", async () => {
      await setUpCsrf();
      stubFetch(mockResponse({ api_version: "v1", data_origin: "test", correlation_id: "c-1", item: {} }, 201));
      const result = await createRule({
        code: "TEST", name: "Test", dataset_id: "ds-1", rule_type: "REQUIRED",
        primary_dimension: "COMPLETENESS", threshold: 100, weight: 1, criticality: "MEDIUM", owner_user_id: "user-1", parameters: {},
      });
      expect(result).toMatchObject({ correlation_id: "c-1" });
    });
  });

  describe("createRuleVersion", () => {
    it("başarılı sürüm oluşturma", async () => {
      await setUpCsrf();
      stubFetch(mockResponse({ api_version: "v1", data_origin: "test", correlation_id: "c-1", item: {} }, 201));
      const result = await createRuleVersion("rule-1", { threshold: 90, weight: 1.5, criticality: "HIGH", parameters: {} });
      expect(result).toMatchObject({ correlation_id: "c-1" });
    });
  });

  describe("testRule", () => {
    it("başarılı test sonucu döndürür", async () => {
      await setUpCsrf();
      stubFetch(mockResponse({
        rule_test_result_id: "tr-1", rule_version_id: "rv-1", status: "SUCCESS",
        record_limit: 10000, checked_count: 1000, passed_count: 950, failed_count: 50,
        not_evaluated_count: 0, success_rate: 95.0, preview_score: 95.0,
        official_score_included: false, error_class: null, message: "Test başarılı",
        created_at: "2026-07-24T10:00:00Z",
      }));
      const result = await testRule("rule-1", { rule_version_id: "rv-1", limit: 10000 });
      expect(result.success_rate).toBe(95.0);
      expect(result.passed_count).toBe(950);
    });
  });

  describe("activateRule", () => {
    it("başarılı aktivasyon", async () => {
      await setUpCsrf();
      stubFetch(mockResponse({ api_version: "v1", data_origin: "test", correlation_id: "c-1", item: {} }));
      const result = await activateRule("rule-1");
      expect(result).toMatchObject({ correlation_id: "c-1" });
    });
  });

  describe("requestRuleApproval", () => {
    it("başarılı onay isteği", async () => {
      await setUpCsrf();
      stubFetch(mockResponse({ api_version: "v1", data_origin: "test", correlation_id: "c-1", item: {} }, 201));
      const result = await requestRuleApproval("rule-1");
      expect(result).toMatchObject({ correlation_id: "c-1" });
    });
  });

  describe("decideRuleApproval", () => {
    it("başarılı onay kararı", async () => {
      await setUpCsrf();
      stubFetch(mockResponse({ api_version: "v1", data_origin: "test", correlation_id: "c-1", item: {} }));
      const result = await decideRuleApproval("approval-1", { approval_request_id: "approval-1", decision: "APPROVE", reason_code: "RULE_OK" });
      expect(result).toMatchObject({ correlation_id: "c-1" });
    });
  });

  describe("withdrawRuleApproval", () => {
    it("başarılı geri çekme", async () => {
      await setUpCsrf();
      stubFetch(mockResponse({ api_version: "v1", data_origin: "test", correlation_id: "c-1", item: {} }));
      const result = await withdrawRuleApproval("approval-1", { approval_request_id: "approval-1", reason_code: "CHANGED_MIND" });
      expect(result).toMatchObject({ correlation_id: "c-1" });
    });
  });

  describe("passivateRule", () => {
    it("başarılı pasifleştirme", async () => {
      await setUpCsrf();
      stubFetch(mockResponse({ api_version: "v1", data_origin: "test", correlation_id: "c-1", item: {} }));
      const result = await passivateRule("rule-1");
      expect(result).toMatchObject({ correlation_id: "c-1" });
    });
  });

  describe("hata durumları", () => {
    it("409 çakışma hatası", async () => {
      await setUpCsrf();
      stubFetch(new Response(null, { status: 409, headers: { "X-Correlation-ID": "c-conflict" } }));
      await expect(activateRule("rule-1")).rejects.toEqual(new RuleApiError("conflict", "c-conflict"));
    });

    it("403 yetki hatası", async () => {
      await setUpCsrf();
      stubFetch(new Response(null, { status: 403, headers: { "X-Correlation-ID": "c-auth" } }));
      await expect(activateRule("rule-1")).rejects.toEqual(new RuleApiError("unauthorized", "c-auth"));
    });

    it("503 teknik hata", async () => {
      await setUpCsrf();
      stubFetch(new Response(null, { status: 503, headers: { "X-Correlation-ID": "c-tech" } }));
      await expect(activateRule("rule-1")).rejects.toEqual(new RuleApiError("technical", "c-tech"));
    });
  });
});