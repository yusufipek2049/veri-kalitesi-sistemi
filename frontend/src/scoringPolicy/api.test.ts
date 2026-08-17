import { afterEach, describe, expect, it, vi } from "vitest";
import {
  decideScoringConfigurationApproval,
  fetchScoringConfigurations,
  ScoringPolicyApiError,
  submitScoringConfiguration,
} from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("skorlama politikası API istemcisi", () => {
  it("konfigürasyon listesini başarılı yanıtla döndürür", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({
        api_version: "v1",
        data_origin: "test",
        correlation_id: "c-1",
        active_configuration_id: "config-1",
        pending_approval: null,
        items: [],
      }),
      { status: 200 },
    ));
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchScoringConfigurations()).resolves.toMatchObject({
      correlation_id: "c-1",
      active_configuration_id: "config-1",
      items: [],
    });
    expect(String(fetchMock.mock.calls[0][0])).toContain("/api/v1/scoring-configurations");
  });

  it("yetki reddini ayrı hata türüyle taşır", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(null, { status: 403, headers: { "X-Correlation-ID": "c-denied" } }),
    ));
    await expect(fetchScoringConfigurations()).rejects.toEqual(
      new ScoringPolicyApiError("unauthorized", "c-denied"),
    );
    await expect(fetchScoringConfigurations()).rejects.toThrow(
      "Skorlama politikası için yetkiniz yok. İzleme kodu: c-denied.",
    );
  });

  it("doğrulama hatasını validation türüyle sınıflandırır", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(null, { status: 400, headers: { "X-Correlation-ID": "c-bad" } }),
    ));
    await expect(
      submitScoringConfiguration({ version: "SCORING_CFG_V2" }),
    ).rejects.toEqual(new ScoringPolicyApiError("validation", "c-bad"));
  });

  it("teknik hatayı güvenli hata türüne dönüştürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(null, { status: 503, headers: { "X-Correlation-ID": "c-error" } }),
    ));
    await expect(fetchScoringConfigurations()).rejects.toEqual(
      new ScoringPolicyApiError("technical", "c-error"),
    );
  });

  it("öneri gövdesini JSON olarak gönderir", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({
        api_version: "v1",
        data_origin: "test",
        correlation_id: "c-2",
        configuration: {},
        approval: {},
      }),
      { status: 201 },
    ));
    vi.stubGlobal("fetch", fetchMock);
    await submitScoringConfiguration({
      version: "SCORING_CFG_V2",
      critical_upper_exclusive: "60.00",
    });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toMatchObject({
      version: "SCORING_CFG_V2",
      critical_upper_exclusive: "60.00",
    });
  });

  it("karar isteğini approval kimliğiyle adresler", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({
        api_version: "v1",
        data_origin: "test",
        correlation_id: "c-3",
        configuration: {},
        approval: {},
      }),
      { status: 200 },
    ));
    vi.stubGlobal("fetch", fetchMock);
    await decideScoringConfigurationApproval("approval-1", {
      decision: "APPROVE",
      reason_code: "SCORING.CONFIGURATION.REVIEWED",
    });
    expect(String(fetchMock.mock.calls[0][0])).toContain(
      "/api/v1/scoring-configurations/approvals/approval-1/decision",
    );
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init.body)).toEqual({
      decision: "APPROVE",
      reason_code: "SCORING.CONFIGURATION.REVIEWED",
    });
  });
});
