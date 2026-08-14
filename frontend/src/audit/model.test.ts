import { describe, expect, it } from "vitest";
import {
  auditPageFromApi,
  auditSummaryFromApi,
  defaultAuditFilters,
  type AuditEventListApiResponse,
  type AuditSummaryResponse,
} from "./model";

describe("audit model", () => {
  it("veri-minimum API yanıtını ekran modeline dönüştürür", () => {
    const page = auditPageFromApi(fixture());

    expect(page).toMatchObject({
      integrityValid: true,
      firstInvalidEventId: null,
      nextAfterSequenceNo: 12,
      throughSequenceNo: 40,
    });
    expect(page.items[0]).toMatchObject({
      actorId: "audit-viewer",
      eventId: "audit-event-1",
      result: "SUCCESS",
      sequenceNo: 11,
      oldValueSummary: { threshold: 80 },
      newValueSummary: { threshold: 85 },
      redactedFields: ["secret_field"],
      eventHash: "abc123",
      previousEventHash: "def456",
    });
  });

  it("first_invalid_event_id alanını doğru eşleştirir", () => {
    const response = fixture();
    const page = auditPageFromApi({ ...response, first_invalid_event_id: "bad-event-1" });
    expect(page.firstInvalidEventId).toBe("bad-event-1");
  });

  it("null/eksik detay alanlarını güvenli varsayılanlarla eşleştirir", () => {
    const response = fixture();
    const sparseItem = { ...response.items[0], old_value_summary: null, new_value_summary: null, redacted_fields: undefined as unknown as string[], event_hash: undefined as unknown as string, previous_event_hash: undefined as unknown as string };
    const page = auditPageFromApi({ ...response, items: [sparseItem] });
    expect(page.items[0].oldValueSummary).toBeNull();
    expect(page.items[0].newValueSummary).toBeNull();
    expect(page.items[0].redactedFields).toEqual([]);
    expect(page.items[0].eventHash).toBe("");
    expect(page.items[0].previousEventHash).toBe("");
  });

  it("özel dönem filtrelerini ve summary yanıtını ekran modelinde taşır", () => {
    expect(defaultAuditFilters).toMatchObject({ periodStart: null, periodEnd: null });
    const response: AuditSummaryResponse = {
      total_count: 50,
      result_distribution: { SUCCESS: 45, FAILURE: 3, DENIED: 2 },
      action_distribution: { RULE_ACTIVATION: 12 },
      top_actors: [{ actor_id: "audit-user", count: 15 }],
      period_start: "2026-08-01T00:00:00Z",
      period_end: "2026-08-11T12:00:00Z",
    };

    expect(auditSummaryFromApi(response)).toEqual({
      totalCount: 50,
      resultDistribution: { SUCCESS: 45, FAILURE: 3, DENIED: 2 },
      actionDistribution: { RULE_ACTIVATION: 12 },
      topActors: [{ actorId: "audit-user", count: 15 }],
      periodStart: "2026-08-01T00:00:00Z",
      periodEnd: "2026-08-11T12:00:00Z",
    });
  });
});

function fixture(): AuditEventListApiResponse {
  return {
    api_version: "v1",
    data_origin: "synthetic-test",
    correlation_id: "audit-model",
    period_start: "2026-07-16T12:00:00Z",
    period_end: "2026-07-23T12:00:00Z",
    integrity_valid: true,
    integrity_checked_count: 1,
    first_invalid_event_id: null,
    next_after_sequence_no: 12,
    through_sequence_no: 40,
    page_size: 50,
    policy_version: "AUDIT_TEST_V1",
    items: [
      {
        sequence_no: 11,
        event_id: "audit-event-1",
        occurred_at: "2026-07-23T11:00:00Z",
        actor_id: "audit-viewer",
        actor_type: "USER",
        correlation_id: "audit-item",
        action: "AUDIT_RECORDS_VIEWED",
        object_type: "AuditQuery",
        object_id: null,
        result: "SUCCESS",
        reason_code: "QUERY_COMPLETED",
        redacted_field_count: 2,
        old_value_summary: { threshold: 80 },
        new_value_summary: { threshold: 85 },
        redacted_fields: ["secret_field"],
        event_hash: "abc123",
        previous_event_hash: "def456",
      },
    ],
  };
}
