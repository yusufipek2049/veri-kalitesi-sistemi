import { describe, expect, it } from "vitest";
import { issuesFromApi } from "./model";

describe("issue API modeli", () => {
  it("snake_case yanıtı istemci modeline dönüştürür", () => {
    const [issue] = issuesFromApi({
      api_version: "v1",
      data_origin: "synthetic-test",
      correlation_id: "issue-model-test",
      limit: 100,
      items: [{
        issue_id: "issue-a",
        issue_no: "DQI-001",
        source_event_type: "TECHNICAL",
        trigger_type: "TECHNICAL_ERROR",
        scope_type: "SOURCE",
        scope_id: "source-a",
        status: "ASSIGNED",
        priority: "HIGH",
        occurrence_count: 3,
        version: 4,
        available_actions: ["START_INVESTIGATION"],
        created_at: "2026-07-23T08:00:00Z",
        updated_at: "2026-07-23T09:00:00Z",
        last_seen_at: "2026-07-23T09:00:00Z",
      }],
    });

    expect(issue).toMatchObject({
      id: "issue-a",
      issueNo: "DQI-001",
      sourceEventType: "TECHNICAL",
      occurrenceCount: 3,
      version: 4,
      availableActions: ["START_INVESTIGATION"],
    });
  });
});
