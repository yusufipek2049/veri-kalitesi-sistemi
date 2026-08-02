import { describe, expect, it } from "vitest";
import { reportScheduleFromApi, reportSummaryFromApi, syntheticSchedules, type ReportCreateApiResponse, type ReportItem, type ReportListApiResponse, type ReportSchedule, type ReportSummaryApiResponse } from "./model";

describe("report model", () => {
  it("ondalık skorları dönüştürür, eksik ve teknik skorları null bırakır", () => {
    const summary = reportSummaryFromApi(fixture());

    expect(summary.averageScore).toBe(87.1);
    expect(summary.rows[0].scoreValue).toBe(91.8);
    expect(summary.rows[1]).toMatchObject({
      scoreStatus: "NOT_CALCULATED_TECHNICAL_ERROR",
      scoreValue: null,
    });
  });

  it("rapor talep yanıtında report_id ve status bulunur", () => {
    const response: ReportCreateApiResponse = {
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
    };
    expect(response.report.report_id).toBe("rpt-1");
    expect(response.report.status).toBe("QUEUED");
  });

  it("rapor listesi yanıtı boş olabilir", () => {
    const response: ReportListApiResponse = {
      api_version: "v1",
      data_origin: "test",
      correlation_id: "corr-2",
      items: [],
    };
    expect(response.items).toHaveLength(0);
  });

  it("rapor listesi yanıtı birden çok öğe içerebilir", () => {
    const items: ReportItem[] = [
      {
        report_id: "rpt-1",
        report_type: "SUMMARY",
        format: "PDF",
        status: "READY",
        file_size: 1024,
        expires_at: "2026-07-25T10:00:00Z",
        created_at: "2026-07-24T10:00:00Z",
        completed_at: "2026-07-24T10:05:00Z",
        failure_reason: null,
      },
      {
        report_id: "rpt-2",
        report_type: "DETAIL",
        format: "CSV",
        status: "FAILED",
        file_size: null,
        expires_at: null,
        created_at: "2026-07-24T11:00:00Z",
        completed_at: "2026-07-24T11:01:00Z",
        failure_reason: "Timeout: data too large",
      },
    ];
    const response: ReportListApiResponse = {
      api_version: "v1",
      data_origin: "test",
      correlation_id: "corr-3",
      items,
    };
    expect(response.items).toHaveLength(2);
    expect(response.items[0].status).toBe("READY");
    expect(response.items[0].file_size).toBe(1024);
    expect(response.items[1].status).toBe("FAILED");
    expect(response.items[1].failure_reason).toBe("Timeout: data too large");
  });
});

describe("report schedule model", () => {
  it("schedule API yanıtını dönüştürür", () => {
    const schedule = reportScheduleFromApi({
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
      last_triggered_at: "2026-07-24T08:00:00Z",
    });
    expect(schedule.name).toBe("Günlük Özet");
    expect(schedule.is_active).toBe(true);
    expect(schedule.schedule_type).toBe("DAILY");
  });

  it("pasif schedule dönüşümü", () => {
    const schedule = reportScheduleFromApi({
      schedule_id: "sched-2",
      name: "Pasif Rapor",
      report_type: "DETAIL",
      format: "XLSX",
      schedule_type: "MONTHLY",
      timezone_name: "UTC",
      is_active: false,
      next_run_at: null,
      created_by: "test-user",
      created_at: "2026-07-01T10:00:00Z",
      last_triggered_at: null,
    });
    expect(schedule.is_active).toBe(false);
    expect(schedule.next_run_at).toBeNull();
  });

  it("sentetik schedule verisi doğru yapıda", () => {
    expect(syntheticSchedules).toHaveLength(3);
    expect(syntheticSchedules[0].schedule_type).toBe("DAILY");
    expect(syntheticSchedules[1].schedule_type).toBe("WEEKLY");
    expect(syntheticSchedules[2].is_active).toBe(false);
  });
});

function fixture(): ReportSummaryApiResponse {
  return {
    api_version: "v1",
    data_origin: "synthetic-test",
    correlation_id: "report-model",
    report_type: "SUMMARY",
    created_at: "2026-07-23T12:00:00Z",
    period_start: "2026-06-23T12:00:00Z",
    period_end: "2026-07-23T12:00:00Z",
    source_count: 2,
    calculated_source_count: 1,
    average_score: "87.10",
    policy_version: "REPORT_V1",
    masking_mode: "AGGREGATED_ONLY",
    rows: [
      {
        source_id: "source-a",
        score_value: "91.80",
        score_status: "CALCULATED",
        level: "GOOD",
        calculated_at: "2026-07-23T11:00:00Z",
      },
      {
        source_id: "source-b",
        score_value: null,
        score_status: "NOT_CALCULATED_TECHNICAL_ERROR",
        level: null,
        calculated_at: "2026-07-23T10:00:00Z",
      },
    ],
  };
}
