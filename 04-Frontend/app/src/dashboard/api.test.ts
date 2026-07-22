import { afterEach, describe, expect, it, vi } from "vitest";
import { DashboardApiError, fetchDashboardSummary } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("dashboard API istemcisi", () => {
  it("FR-054 güvenli cookie taşıyarak v1 özetini okur", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(validPayload()), {
      status: 200,
      headers: { "Content-Type": "application/json", "X-Correlation-ID": "correlation-api" },
    }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchDashboardSummary();

    expect(result.has_data).toBe(false);
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/dashboard/summary", expect.objectContaining({
      credentials: "include",
      method: "GET",
    }));
  });

  it("FR-081 401 ve 403 yanıtlarını yetkisiz durumuna dönüştürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", {
      status: 403,
      headers: { "X-Correlation-ID": "correlation-denied" },
    })));

    await expect(fetchDashboardSummary()).rejects.toMatchObject({
      kind: "unauthorized",
      correlationId: "correlation-denied",
    } satisfies Partial<DashboardApiError>);
  });

  it("NFR-USA-003 teknik hata içeriğini UI modeline taşımadan izleme kodunu korur", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("database secret detail", {
      status: 503,
      headers: { "X-Correlation-ID": "correlation-safe" },
    })));

    await expect(fetchDashboardSummary()).rejects.toMatchObject({
      kind: "technical",
      correlationId: "correlation-safe",
      message: "Dashboard API request failed.",
    });
  });

  it("FR-056 operasyonel gösterge zarfı eksik yanıtı reddeder", async () => {
    const payload = validPayload();
    const { operational_indicators: _, ...incompletePayload } = payload;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(incompletePayload), {
      status: 200,
      headers: { "Content-Type": "application/json", "X-Correlation-ID": "correlation-invalid" },
    })));

    await expect(fetchDashboardSummary()).rejects.toMatchObject({
      kind: "invalid-response",
      correlationId: "correlation-invalid",
    });
  });

  it("FR-056 bilinmeyen durum ve negatif sayaçları reddeder", async () => {
    const payload = validPayload();
    const invalidPayload = {
      ...payload,
      operational_indicators: {
        ...payload.operational_indicators,
        technical_errors: {
          ...payload.operational_indicators.technical_errors,
          observation_count: -1,
        },
      },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(invalidPayload), {
      status: 200,
      headers: { "Content-Type": "application/json", "X-Correlation-ID": "correlation-invalid-count" },
    })));

    await expect(fetchDashboardSummary()).rejects.toMatchObject({
      kind: "invalid-response",
      correlationId: "correlation-invalid-count",
    });
  });
});

function validPayload() {
  return {
    api_version: "v1",
    data_origin: "test",
    correlation_id: "correlation-api",
    as_of: "2026-07-22T12:00:00Z",
    has_data: false,
    periods: [],
    operational_indicators: {
      measurement_qualification: {
        status: "NO_DATA",
        evaluated_scope_count: 0,
        reason_codes: ["NO_AUTHORIZED_MEASUREMENT"],
        policy_version: null,
      },
      critical_controls: {
        status: "NOT_AVAILABLE",
        reason_code: "CRITICAL_RULE_RESULT_NOT_AVAILABLE",
        passed_count: null,
        failed_count: null,
        not_evaluated_count: null,
      },
      technical_errors: {
        observation_count: 0,
        execution_count: 0,
        affected_source_count: 0,
        last_occurred_at: null,
      },
    },
  };
}
