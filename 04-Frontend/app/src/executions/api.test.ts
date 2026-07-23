import { afterEach, describe, expect, it, vi } from "vitest";
import { ExecutionApiError, fetchExecutions } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("çalıştırma liste API istemcisi", () => {
  it("başarılı yanıtı döndürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ api_version: "v1", data_origin: "test", correlation_id: "c-1", limit: 100, items: [] }), { status: 200 })));
    await expect(fetchExecutions()).resolves.toMatchObject({ correlation_id: "c-1", items: [] });
  });

  it("yetki reddini ayrı hata türüyle taşır", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 403, headers: { "X-Correlation-ID": "c-denied" } })));
    await expect(fetchExecutions()).rejects.toEqual(new ExecutionApiError("unauthorized", "c-denied"));
  });

  it("teknik hatayı güvenli hata türüne dönüştürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 503, headers: { "X-Correlation-ID": "c-error" } })));
    await expect(fetchExecutions()).rejects.toEqual(new ExecutionApiError("technical", "c-error"));
  });
});
