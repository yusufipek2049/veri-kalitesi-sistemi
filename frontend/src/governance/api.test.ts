import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchGovernanceApprovals, GovernanceApiError } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("yönetişim onay listesi API istemcisi", () => {
  it("görünüm parametresiyle başarılı yanıtı döndürür", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ api_version: "v1", data_origin: "test", correlation_id: "c-1", view: "PENDING", items: [] }),
      { status: 200 },
    ));
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchGovernanceApprovals("PENDING")).resolves.toMatchObject({
      correlation_id: "c-1",
      view: "PENDING",
      items: [],
    });
    const calledUrl = String(fetchMock.mock.calls[0][0]);
    expect(calledUrl).toContain("/api/v1/governance/approval-requests");
    expect(calledUrl).toContain("view=PENDING");
  });

  it("yetki reddini ayrı hata türüyle taşır", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(null, { status: 403, headers: { "X-Correlation-ID": "c-denied" } }),
    ));
    await expect(fetchGovernanceApprovals("ALL")).rejects.toEqual(
      new GovernanceApiError("unauthorized", "c-denied"),
    );
    await expect(fetchGovernanceApprovals("ALL")).rejects.toThrow(
      "Bu yönetişim işlemi için yetkiniz yok. İzleme kodu: c-denied.",
    );
  });

  it("teknik hatayı güvenli hata türüne dönüştürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(null, { status: 503, headers: { "X-Correlation-ID": "c-error" } }),
    ));
    await expect(fetchGovernanceApprovals("ALL")).rejects.toEqual(
      new GovernanceApiError("technical", "c-error"),
    );
  });
});
