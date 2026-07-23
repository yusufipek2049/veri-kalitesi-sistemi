import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchReportSummary, ReportApiError } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("report API", () => {
  it("aynı origin kimlik bilgileriyle özet ister", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ api_version: "v1", rows: [] }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchReportSummary();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/reports/summary",
      expect.objectContaining({ credentials: "same-origin" }),
    );
  });

  it("403 yanıtını yetkisiz hata olarak sınıflandırır", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(null, {
          status: 403,
          headers: { "X-Correlation-ID": "report-denied" },
        }),
      ),
    );

    await expect(fetchReportSummary()).rejects.toEqual(
      expect.objectContaining<Partial<ReportApiError>>({
        kind: "unauthorized",
        correlationId: "report-denied",
      }),
    );
  });
});
