import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchIssues, IssueApiError, startIssueInvestigation } from "./api";

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

  it("CSRF kanıtı ve sürümle inceleme mutasyonu gönderir", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({
        api_version: "v1",
        data_origin: "test",
        correlation_id: "list",
        limit: 100,
        items: [],
      }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": "memory-only-proof",
        },
      }))
      .mockResolvedValueOnce(Response.json({
        api_version: "v1",
        data_origin: "test",
        correlation_id: "mutation",
        item: {
          issue_id: "issue-a",
          issue_no: "DQI-001",
          source_event_type: "QUALITY",
          trigger_type: "QUALITY_THRESHOLD",
          scope_type: "DATASET",
          scope_id: "dataset-a",
          status: "INVESTIGATING",
          priority: "HIGH",
          occurrence_count: 1,
          version: 2,
          available_actions: [],
          created_at: "2026-07-23T08:00:00Z",
          updated_at: "2026-07-23T09:00:00Z",
          last_seen_at: "2026-07-23T08:00:00Z",
        },
      }));
    vi.stubGlobal("fetch", fetchMock);

    await fetchIssues();
    await startIssueInvestigation("issue-a", 1);

    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/v1/issues/issue-a/investigation",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-CSRF-Token": "memory-only-proof" }),
        body: JSON.stringify({ version: 1 }),
      }),
    );
  });

  it("sürüm çakışmasını güvenli conflict hatasına dönüştürür", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response("{}", {
        status: 200,
        headers: { "X-CSRF-Token": "memory-only-proof" },
      }))
      .mockResolvedValueOnce(new Response("", {
        status: 409,
        headers: { "X-Correlation-ID": "issue-conflict" },
      }));
    vi.stubGlobal("fetch", fetchMock);
    await fetchIssues();

    await expect(startIssueInvestigation("issue-a", 1)).rejects.toEqual(
      new IssueApiError("conflict", "issue-conflict"),
    );
  });
});
