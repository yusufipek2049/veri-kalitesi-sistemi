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
});

function validPayload() {
  return {
    api_version: "v1",
    data_origin: "test",
    correlation_id: "correlation-api",
    as_of: "2026-07-22T12:00:00Z",
    has_data: false,
    periods: [],
  };
}
