import { describe, expect, it } from "vitest";
import {
  auditPageFromApi,
  type AuditEventListApiResponse,
} from "./model";

describe("audit model", () => {
  it("veri-minimum API yanıtını ekran modeline dönüştürür", () => {
    const page = auditPageFromApi(fixture());

    expect(page).toMatchObject({
      integrityValid: true,
      nextAfterSequenceNo: 12,
      throughSequenceNo: 40,
    });
    expect(page.items[0]).toMatchObject({
      actorId: "audit-viewer",
      eventId: "audit-event-1",
      result: "SUCCESS",
      sequenceNo: 11,
    });
    expect(page.items[0]).not.toHaveProperty("newValues");
    expect(page.items[0]).not.toHaveProperty("oldValues");
    expect(page.items[0]).not.toHaveProperty("recordHash");
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
      },
    ],
  };
}
