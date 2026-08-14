import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchDashboardOverview } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("dashboard API", () => {
  it("dashboard filtrelerini snake_case query parametrelerine dönüştürür", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ api_version: "v1" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchDashboardOverview({
      scopeType: "SOURCE",
      scopeId: "source-a",
      startDate: "2026-08-01",
      endDate: "2026-08-11",
    });

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    const query = new URL(url, "http://localhost").searchParams;
    expect(query.get("scope_type")).toBe("SOURCE");
    expect(query.get("scope_id")).toBe("source-a");
    expect(query.get("start_date")).toBe("2026-08-01");
    expect(query.get("end_date")).toBe("2026-08-11");
    expect(options).toEqual(expect.objectContaining({ credentials: "same-origin" }));
  });

  it("filtre yokken query string üretmez", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ api_version: "v1" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchDashboardOverview();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/dashboard/overview",
      expect.any(Object),
    );
  });
});
