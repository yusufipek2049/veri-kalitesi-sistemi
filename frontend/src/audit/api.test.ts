import { afterEach, describe, expect, it, vi } from "vitest";
import { AuditApiError, fetchAuditEvents } from "./api";
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
        objectType: "QualityRule",
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
    expect(query.get("object_type")).toBe("QualityRule");
    expect(query.get("result")).toBe("DENIED");
    expect(query.get("after_sequence_no")).toBe("20");
    expect(query.get("period_end")).toBe("2026-07-23T12:00:00Z");
    expect(query.get("through_sequence_no")).toBe("40");
    expect(options).toEqual(expect.objectContaining({ credentials: "same-origin" }));
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
});
