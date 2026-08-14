import { describe, expect, it } from "vitest";
import { dataSourcesFromApi } from "./model";

describe("veri kaynakları görünüm modeli", () => {
  it("backend action ve pending request projection'ını aynen taşır", () => {
    const items = dataSourcesFromApi({
      api_version: "v1",
      data_origin: "test",
      correlation_id: "correlation",
      items: [{
        data_source_id: "source-a",
        name: "Kaynak A",
        source_type: "POSTGRESQL",
        status: "TEST_SUCCEEDED",
        last_test_at: null,
        available_actions: ["APPROVE_ACTIVATION", "REJECT_ACTIVATION"],
        pending_activation_request_id: "request-a",
        pending_activation_maker_actor_id: "maker-a",
        pending_activation_requested_at: "2026-08-05T08:00:00Z",
        pending_activation_expires_at: null,
        pending_deactivation_request_id: null,
        pending_deactivation_maker_actor_id: null,
        pending_deactivation_requested_at: null,
      }],
    });

    expect(items[0]).toMatchObject({
      id: "source-a",
      availableActions: ["APPROVE_ACTIVATION", "REJECT_ACTIVATION"],
      pendingActivationRequestId: "request-a",
      pendingActivationMakerActorId: "maker-a",
    });
  });
});
