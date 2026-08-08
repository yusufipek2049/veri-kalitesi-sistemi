import { afterEach, describe, expect, it, vi } from "vitest";
import { createReport, createSchedule, deleteSchedule, fetchReportSummary, fetchSchedules, getReport, listReports, ReportApiError, triggerDownload } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("report API", () => {
  it("aynı origin kimlik bilgileriyle özet ister", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ api_version: "v1", rows: [] }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchReportSummary();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/reports/summary",
      expect.objectContaining({ credentials: "same-origin" }),
    );
  });

  it("403 yanıtını yetkisiz hata olarak sınıflandırır", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(null, {
          status: 403,
          headers: { "X-Correlation-ID": "report-denied" },
        }),
      ),
    );

    await expect(fetchReportSummary()).rejects.toEqual(
      expect.objectContaining<Partial<ReportApiError>>({
        kind: "unauthorized",
        correlationId: "report-denied",
      }),
    );
  });

  it("createReport POST isteği gönderir", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          api_version: "v1",
          data_origin: "test",
          correlation_id: "corr-1",
          report: {
            report_id: "rpt-1",
            report_type: "SUMMARY",
            format: "PDF",
            status: "QUEUED",
            file_size: null,
            expires_at: null,
            created_at: "2026-07-24T10:00:00Z",
            completed_at: null,
            failure_reason: null,
          },
        }),
        { status: 202 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await createReport({
      report_type: "SUMMARY",
      format: "PDF",
      parameters: {},
      reason_code: "TEST_RAPOR",
      sensitivity_level: null,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/reports/",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          report_type: "SUMMARY",
          format: "PDF",
          parameters: {},
          reason_code: "TEST_RAPOR",
          sensitivity_level: null,
        }),
      }),
    );
    expect(result.report.report_id).toBe("rpt-1");
    expect(result.report.status).toBe("QUEUED");
  });

  it("listReports GET isteği gönderir", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          api_version: "v1",
          data_origin: "test",
          correlation_id: "corr-2",
          items: [],
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await listReports(10, 0);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/reports/?limit=10&offset=0",
      expect.objectContaining({ credentials: "same-origin" }),
    );
    expect(result.items).toHaveLength(0);
  });

  it("getReport rapor detayını getirir", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          api_version: "v1",
          data_origin: "test",
          correlation_id: "corr-3",
          report: {
            report_id: "rpt-1",
            report_type: "SUMMARY",
            format: "PDF",
            status: "READY",
            file_size: 2048,
            expires_at: "2026-07-25T10:00:00Z",
            created_at: "2026-07-24T10:00:00Z",
            completed_at: "2026-07-24T10:05:00Z",
            failure_reason: null,
          },
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getReport("rpt-1");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/reports/rpt-1",
      expect.objectContaining({ credentials: "same-origin" }),
    );
    expect(result.report.status).toBe("READY");
    expect(result.report.file_size).toBe(2048);
  });

  it("triggerDownload blob indirme işlemi yapar", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("test-content", {
        status: 200,
        headers: { "Content-Type": "application/pdf" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const createObjectURL = vi.fn().mockReturnValue("blob:test-url");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });

    const anchorClick = vi.fn();
    const anchorRemove = vi.fn();
    const createElement = vi.fn().mockReturnValue({
      href: "",
      download: "",
      click: anchorClick,
      remove: anchorRemove,
    });
    vi.stubGlobal("document", {
      body: { appendChild: vi.fn(), removeChild: vi.fn() },
      createElement,
    });

    await triggerDownload("rpt-1", "report.pdf");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/reports/rpt-1/download",
      expect.objectContaining({ credentials: "same-origin" }),
    );
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(anchorClick).toHaveBeenCalled();
  });

  it("fetchSchedules GET isteği gönderir", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          api_version: "v1",
          data_origin: "test",
          correlation_id: "corr-sched",
          items: [],
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchSchedules();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/report-schedules",
      expect.objectContaining({ credentials: "same-origin" }),
    );
    expect(result.items).toHaveLength(0);
  });

  it("createSchedule POST isteği gönderir", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          api_version: "v1",
          data_origin: "test",
          correlation_id: "corr-sched-create",
          item: {
            schedule_id: "sched-1",
            name: "Günlük Özet",
            report_type: "SUMMARY",
            format: "PDF",
            schedule_type: "DAILY",
            timezone_name: "Europe/Istanbul",
            is_active: true,
            next_run_at: "2026-07-25T08:00:00Z",
            created_by: "test-user",
            created_at: "2026-07-24T10:00:00Z",
            last_triggered_at: null,
          },
          preview: ["2026-07-25T08:00:00Z"],
        }),
        { status: 201 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await createSchedule({
      name: "Günlük Özet",
      report_type: "SUMMARY",
      format: "PDF",
      schedule_type: "DAILY",
      timezone_name: "Europe/Istanbul",
      parameters: {},
      sensitivity_level: null,
      recipients: [],
      local_time: "08:00",
      once_at: null,
      day_of_week: null,
      day_of_month: null,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/report-schedules",
      expect.objectContaining({ method: "POST" }),
    );
    expect(result.item.schedule_id).toBe("sched-1");
    expect(result.preview).toHaveLength(1);
  });

  it("deleteSchedule DELETE isteği gönderir", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          api_version: "v1",
          data_origin: "test",
          correlation_id: "corr-sched-del",
          deleted: true,
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await deleteSchedule("sched-1");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/report-schedules/sched-1",
      expect.objectContaining({ method: "DELETE" }),
    );
    expect(result.deleted).toBe(true);
  });
});