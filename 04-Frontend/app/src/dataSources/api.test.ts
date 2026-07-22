import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchDataSources } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("veri kaynakları API istemcisi", () => {
  it("salt okunur listeyi güvenli oturum bilgisiyle alır", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ api_version: "v1", data_origin: "test", correlation_id: "correlation", items: [] }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchDataSources();

    expect(result.items).toEqual([]);
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/data-sources", expect.objectContaining({ credentials: "same-origin" }));
  });

  it("401 ve 403 yanıtlarını yetkisiz duruma dönüştürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 403, headers: { "X-Correlation-ID": "denied" } })));

    await expect(fetchDataSources()).rejects.toMatchObject({ kind: "unauthorized", correlationId: "denied" });
  });

  it("teknik yanıt gövdesini kullanıcı modeline taşımaz", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("secret stack trace", { status: 503, headers: { "X-Correlation-ID": "safe" } })));

    await expect(fetchDataSources()).rejects.toMatchObject({ kind: "technical", correlationId: "safe", message: "Data source list request failed." });
  });
});
