import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createDataSource,
  decideDataSourceActivation,
  fetchDataSources,
  passivateDataSource,
  requestDataSourceActivation,
} from "./api";

const apiItem = {
  data_source_id: "source-a",
  name: "Kaynak A",
  source_type: "POSTGRESQL",
  status: "TEST_SUCCEEDED",
  last_test_at: null,
  available_actions: ["REQUEST_ACTIVATION"],
  pending_activation_request_id: null,
  pending_activation_maker_actor_id: null,
  pending_activation_requested_at: null,
  pending_activation_expires_at: null,
};

afterEach(() => vi.unstubAllGlobals());

async function acquireCsrf(): Promise<void> {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
    api_version: "v1", data_origin: "test", correlation_id: "init", items: [],
  }), { status: 200, headers: { "X-CSRF-Token": "proof-a" } })));
  await fetchDataSources();
}

function success(status = 200): Response {
  return new Response(JSON.stringify({
    api_version: "v1",
    data_origin: "test",
    correlation_id: "correlation-a",
    item: apiItem,
    activation_request_status: null,
    replayed: false,
  }), { status, headers: { "Content-Type": "application/json" } });
}

describe("veri kaynağı API sözleşmesi", () => {
  it("create raw secret veya owner göndermeden TLS alanlarını taşır", async () => {
    await acquireCsrf();
    const fetchMock = vi.fn().mockResolvedValue(success(201));
    vi.stubGlobal("fetch", fetchMock);
    await createDataSource({
      name: "Kaynak A", source_type: "POSTGRESQL", host: "db.internal", port: 5432,
      database: "analytics", schema: "public", secret_reference: "secret://local/source-a",
      ssl_mode: "verify-full", connect_timeout_seconds: 5, statement_timeout_ms: 5000,
    });
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    const body = JSON.parse(String(init.body));
    expect(body).not.toHaveProperty("owner_user_id");
    expect(body).not.toHaveProperty("username");
    expect(body).not.toHaveProperty("password");
    expect(body).toMatchObject({ secret_reference: "secret://local/source-a", ssl_mode: "verify-full" });
    expect(init.headers).toMatchObject({ "X-CSRF-Token": "proof-a" });
  });

  it("aktivasyon talebini source endpoint'ine gönderir", async () => {
    await acquireCsrf();
    const fetchMock = vi.fn().mockResolvedValue(success(201));
    vi.stubGlobal("fetch", fetchMock);
    await requestDataSourceActivation("source/a");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/data-sources/source%2Fa/activation");
  });

  it("kararı request-centric path ve APPROVE body ile gönderir", async () => {
    await acquireCsrf();
    const fetchMock = vi.fn().mockResolvedValue(success());
    vi.stubGlobal("fetch", fetchMock);
    await decideDataSourceActivation("request/a", "APPROVE", "VALIDATED");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/data-source-activation-requests/request%2Fa/decision");
    expect(JSON.parse(String(fetchMock.mock.calls[0][1].body))).toEqual({ decision: "APPROVE", reason_code: "VALIDATED" });
  });

  it("pasifleştirme gerekçe kodunu body'de taşır", async () => {
    await acquireCsrf();
    const fetchMock = vi.fn().mockResolvedValue(success());
    vi.stubGlobal("fetch", fetchMock);
    await passivateDataSource("source-a", "RETIRED");
    expect(JSON.parse(String(fetchMock.mock.calls[0][1].body))).toEqual({ reason_code: "RETIRED" });
  });

  it("structured problem alanlarını korur", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      code: "DATA_SOURCE_MAKER_CHECKER_VIOLATION",
      detail: "safe detail",
      correlation_id: "denied-a",
    }), { status: 403, headers: { "Content-Type": "application/problem+json" } })));
    await expect(fetchDataSources()).rejects.toMatchObject({
      httpStatus: 403,
      code: "DATA_SOURCE_MAKER_CHECKER_VIOLATION",
      detail: "safe detail",
      correlationId: "denied-a",
      kind: "unauthorized",
    });
  });
});
