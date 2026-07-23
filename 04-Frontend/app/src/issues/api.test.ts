import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchIssues, IssueApiError } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("issue API istemcisi", () => {
  it("yetkisiz yanıtı güvenli istemci hatasına dönüştürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", {
      status: 403,
      headers: { "X-Correlation-ID": "issue-forbidden" },
    })));

    await expect(fetchIssues()).rejects.toEqual(
      new IssueApiError("unauthorized", "issue-forbidden"),
    );
  });

  it("başarılı yanıtı döndürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({
      api_version: "v1",
      data_origin: "synthetic-test",
      correlation_id: "issue-ok",
      limit: 100,
      items: [],
    })));

    await expect(fetchIssues()).resolves.toMatchObject({ correlation_id: "issue-ok" });
  });
});
