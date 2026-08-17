import { afterEach, describe, expect, it, vi } from "vitest";
import {
  JobsApiError,
  createSchedule,
  fetchScheduleProposals,
  fetchSchedules,
  setScheduleActive,
} from "./api";

afterEach(() => vi.unstubAllGlobals());

const schedulePayload = {
  name: "Hesap mutabakat job'u",
  dataset_id: "ds-1",
  schedule_type: "INTERVAL" as const,
  timezone_name: "Europe/Istanbul",
  rule_version_ids: ["rv-1"],
  interval_minutes: 10,
};

describe("zamanlayıcı liste API istemcisi", () => {
  it("başarılı yanıtı döndürür", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ api_version: "v1", data_origin: "test", correlation_id: "c-1", items: [] }),
          { status: 200 },
        ),
      ),
    );
    await expect(fetchSchedules()).resolves.toMatchObject({ correlation_id: "c-1", items: [] });
  });

  it("yetkisiz erişimi unauthorized hata türüyle taşır", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(null, { status: 401, headers: { "X-Correlation-ID": "c-auth" } }),
      ),
    );
    await expect(fetchSchedules()).rejects.toEqual(
      new JobsApiError("unauthorized", "The schedule request could not be completed.", "c-auth"),
    );
  });
});

describe("zamanlayıcı öneri API istemcisi", () => {
  it("öneri yanıtını döndürür ve dataset kimliğini yol parametresine taşır", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          api_version: "v1",
          data_origin: "test",
          correlation_id: "c-prop",
          dataset_id: "ds-near",
          timeliness_nature: "NEAR_TIME",
          band: "INTERVAL 5-15 dakika",
          proposals: [],
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const result = await fetchScheduleProposals("ds-near");
    expect(result.band).toBe("INTERVAL 5-15 dakika");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/datasets/ds-near/schedule-proposals",
      expect.anything(),
    );
  });

  it("bulunamadı hatasını not_found türüne dönüştürür", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(null, { status: 404, headers: { "X-Correlation-ID": "c-nf" } }),
      ),
    );
    await expect(fetchScheduleProposals("missing")).rejects.toEqual(
      new JobsApiError("not_found", "The schedule request could not be completed.", "c-nf"),
    );
  });
});

describe("zamanlayıcı oluşturma API istemcisi", () => {
  it("başarılı oluşturma yanıtını döndürür", async () => {
    const body = {
      api_version: "v1",
      data_origin: "test",
      correlation_id: "c-created",
      schedule_id: "sch-new",
      preview_runs: ["2026-08-17T09:10:00Z"],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 201 })),
    );
    const result = await createSchedule(schedulePayload);
    expect(result.schedule_id).toBe("sch-new");
    expect(result.preview_runs).toHaveLength(1);
  });

  it("bant dışı 409 yanıtını governance_approval_required olarak ayrıştırır", async () => {
    const problem = JSON.stringify({
      code: "EXECUTION_GOVERNANCE_APPROVAL_REQUIRED",
      governance_request_type: "SCHEDULE_INTERVAL_EXCEPTION",
      detail: "Governance approval required",
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(problem, { status: 409, headers: { "X-Correlation-ID": "c-gov" } }),
      ),
    );
    await expect(
      createSchedule({ ...schedulePayload, interval_minutes: 30 }),
    ).rejects.toEqual(
      new JobsApiError(
        "governance_approval_required",
        "Governance approval required",
        "c-gov",
        "SCHEDULE_INTERVAL_EXCEPTION",
      ),
    );
  });

  it("gövdesiz 409 yanıtını jenerik conflict olarak sınıflandırır", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(null, { status: 409, headers: { "X-Correlation-ID": "c-plain" } }),
      ),
    );
    await expect(createSchedule(schedulePayload)).rejects.toEqual(
      new JobsApiError("conflict", "The schedule request could not be completed.", "c-plain"),
    );
  });

  it("doğrulama hatasını validation türüne ve detay metnine dönüştürür", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Kural sürümü dataset ile uyumsuz." }), {
          status: 422,
          headers: { "X-Correlation-ID": "c-invalid" },
        }),
      ),
    );
    await expect(createSchedule(schedulePayload)).rejects.toEqual(
      new JobsApiError("validation", "Kural sürümü dataset ile uyumsuz.", "c-invalid"),
    );
  });
});

describe("zamanlayıcı aktiflik API istemcisi", () => {
  it("aktif/pasif eylemini doğru endpoint'e POST eder", async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(() =>
        Promise.resolve(new Response(JSON.stringify({ schedule_id: "sch-1" }), { status: 200 })),
      );
    vi.stubGlobal("fetch", fetchMock);

    await setScheduleActive("sch-1", true);
    expect(fetchMock).toHaveBeenLastCalledWith("/api/v1/schedules/sch-1/activate", expect.anything());

    await setScheduleActive("sch-1", false);
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/v1/schedules/sch-1/deactivate",
      expect.anything(),
    );
  });
});
