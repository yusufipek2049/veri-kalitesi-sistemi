import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { AuditRoute } from "./AuditRoute";
import { syntheticAuditPage, syntheticAuditSummary, type AuditEventListItem } from "./model";

const apiMocks = vi.hoisted(() => ({
  fetchAuditEvents: vi.fn(),
  fetchAuditSummary: vi.fn(),
}));

vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api")>()),
  fetchAuditEvents: apiMocks.fetchAuditEvents,
  fetchAuditSummary: apiMocks.fetchAuditSummary,
}));

function apiPage(items: AuditEventListItem[]) {
  return {
    api_version: "v1" as const,
    data_origin: "test",
    correlation_id: "request-correlation",
    period_start: syntheticAuditPage.periodStart,
    period_end: syntheticAuditPage.periodEnd,
    integrity_valid: true,
    integrity_checked_count: items.length,
    first_invalid_event_id: null,
    next_after_sequence_no: null,
    through_sequence_no: items.length,
    page_size: 50,
    policy_version: "TEST_V1",
    items: items.map((item) => ({
      sequence_no: item.sequenceNo,
      event_id: item.eventId,
      occurred_at: item.occurredAt,
      actor_id: item.actorId,
      actor_type: item.actorType,
      correlation_id: item.correlationId,
      action: item.action,
      object_type: item.objectType,
      object_id: item.objectId,
      result: item.result,
      reason_code: item.reasonCode,
      redacted_field_count: item.redactedFieldCount,
      old_value_summary: item.oldValueSummary,
      new_value_summary: item.newValueSummary,
      redacted_fields: item.redactedFields,
      event_hash: item.eventHash,
      previous_event_hash: item.previousEventHash,
    })),
  };
}

const apiSummary = {
  total_count: syntheticAuditSummary.totalCount,
  result_distribution: syntheticAuditSummary.resultDistribution,
  action_distribution: syntheticAuditSummary.actionDistribution,
  top_actors: syntheticAuditSummary.topActors.map((actor) => ({
    actor_id: actor.actorId,
    count: actor.count,
  })),
  period_start: syntheticAuditSummary.periodStart,
  period_end: syntheticAuditSummary.periodEnd,
};

describe("AuditRoute canlı yenileme", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    apiMocks.fetchAuditEvents.mockReset();
    apiMocks.fetchAuditSummary.mockReset();
  });

  afterEach(() => vi.useRealTimers());

  it("seçilen aralıkta yükler, yeni olay banner'ını gösterir ve unmount'ta intervali temizler", async () => {
    const firstItems = syntheticAuditPage.items.slice(0, 1);
    const newItem = { ...syntheticAuditPage.items[1], eventId: "audit-new", sequenceNo: 7 };
    apiMocks.fetchAuditEvents
      .mockResolvedValueOnce(apiPage(firstItems))
      .mockResolvedValue(apiPage([...firstItems, newItem]));
    apiMocks.fetchAuditSummary.mockResolvedValue(apiSummary);

    const { unmount } = render(
      <ThemeModeProvider>
        <MemoryRouter><AuditRoute /></MemoryRouter>
      </ThemeModeProvider>,
    );
    await act(async () => { await Promise.resolve(); });

    fireEvent.mouseDown(screen.getByLabelText("Otomatik yenileme"));
    fireEvent.click(screen.getByRole("option", { name: "30 sn" }));
    await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });

    expect(apiMocks.fetchAuditEvents).toHaveBeenCalledTimes(2);
    expect(screen.getByText("1 yeni olay yüklendi")).toBeVisible();

    unmount();
    await vi.advanceTimersByTimeAsync(30_000);
    expect(apiMocks.fetchAuditEvents).toHaveBeenCalledTimes(2);
  });
});
