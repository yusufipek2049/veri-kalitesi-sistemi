import { afterEach, describe, expect, it, vi } from "vitest";
import {
  AuditApiError,
  fetchAuditEvents,
  fetchAuditExport,
  fetchGroupedAuditEvents,
  fetchAuditSummary,
} from "./api";
import { defaultAuditFilters } from "./model";

afterEach(() => vi.unstubAllGlobals());

describe("audit API", () => {
  it("filtreleri ve snapshot sayfalamasını aynı origin isteğine ekler", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ api_version: "v1", items: [] }), {
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchAuditEvents(
      {
        ...defaultAuditFilters,
        action: "RULE_ACTIVATION",
        actorId: "audit-user",
        objectId: "rule-42",
        result: "DENIED",
      },
      {
        afterSequenceNo: 20,
        periodEnd: "2026-07-23T12:00:00Z",
        throughSequenceNo: 40,
      },
    );

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    const query = new URL(url, "http://localhost").searchParams;
    expect(query.get("actor_id")).toBe("audit-user");
    expect(query.get("action")).toBe("RULE_ACTIVATION");
    expect(query.get("object_type")).toBeNull();
    expect(query.get("object_id")).toBe("rule-42");
    expect(query.get("result")).toBe("DENIED");
    expect(query.get("after_sequence_no")).toBe("20");
    expect(query.get("period_end")).toBe("2026-07-23T12:00:00Z");
    expect(query.get("through_sequence_no")).toBe("40");
    expect(options).toEqual(expect.objectContaining({ credentials: "same-origin" }));
  });

  it("correlation_id filtresini istek parametresine ekler", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ api_version: "v1", items: [] }), {
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchAuditEvents({
      ...defaultAuditFilters,
      correlationId: "corr-abc-123",
    });

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    const query = new URL(url, "http://localhost").searchParams;
    expect(query.get("correlation_id")).toBe("corr-abc-123");
  });

  it("boş correlation_id'yi istek parametresine eklemez", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ api_version: "v1", items: [] }), {
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchAuditEvents({
      ...defaultAuditFilters,
      correlationId: "",
    });

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    const query = new URL(url, "http://localhost").searchParams;
    expect(query.has("correlation_id")).toBe(false);
  });

  it("grouped endpointine zorunlu correlation kimliğiyle istek gönderir", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ api_version: "v1", items: [] }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchGroupedAuditEvents("corr/group 42");

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    const parsed = new URL(url, "http://localhost");
    expect(parsed.pathname).toBe("/api/v1/audit/events/grouped");
    expect(parsed.searchParams.get("correlation_id")).toBe("corr/group 42");
    expect(options).toEqual(expect.objectContaining({ credentials: "same-origin" }));
  });

  it("özel tarih aralığında days yerine period_start ve period_end gönderir", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ api_version: "v1", items: [] }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchAuditEvents({
      ...defaultAuditFilters,
      periodStart: "2026-08-01T00:00:00Z",
      periodEnd: "2026-08-10T23:59:59Z",
    });

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    const query = new URL(url, "http://localhost").searchParams;
    expect(query.has("days")).toBe(false);
    expect(query.get("period_start")).toBe("2026-08-01T00:00:00Z");
    expect(query.get("period_end")).toBe("2026-08-10T23:59:59Z");
  });

  it("summary endpointine aktif filtreleri gönderir", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ total_count: 0 }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchAuditSummary({
      ...defaultAuditFilters,
      actorId: "audit-user",
      action: "RULE_ACTIVATION",
      correlationId: "summary-için-desteklenmiyor",
    });

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    const query = new URL(url, "http://localhost").searchParams;
    expect(url).toContain("/api/v1/audit/summary?");
    expect(query.get("actor_id")).toBe("audit-user");
    expect(query.get("action")).toBe("RULE_ACTIVATION");
    expect(query.has("correlation_id")).toBe(false);
  });

  it("403 yanıtını veri göstermeyen yetkisiz hata olarak sınıflandırır", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(null, {
          status: 403,
          headers: { "X-Correlation-ID": "audit-denied" },
        }),
      ),
    );

    await expect(fetchAuditEvents(defaultAuditFilters)).rejects.toEqual(
      expect.objectContaining<Partial<AuditApiError>>({
        kind: "unauthorized",
        correlationId: "audit-denied",
      }),
    );
  });

  it("dışa aktarma filtrelerini ve formatını gönderip Blob döndürür", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("sequence_no\n1\n", {
        status: 200,
        headers: { "Content-Type": "text/csv" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchAuditExport(
      { ...defaultAuditFilters, action: "RULE_ACTIVATION", correlationId: "corr-export" },
      "csv",
    );

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    const query = new URL(url, "http://localhost").searchParams;
    expect(query.get("format")).toBe("csv");
    expect(query.get("action")).toBe("RULE_ACTIVATION");
    expect(query.get("correlation_id")).toBe("corr-export");
    expect(options.headers).toEqual({ Accept: "text/csv" });
    expect(result).toEqual(expect.objectContaining({ size: 14, type: "text/csv" }));
  });
});
