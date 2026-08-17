import { describe, expect, it } from "vitest";
import {
  jobFromApi,
  jobsFromApi,
  scheduleProposalsFromApi,
  scheduleSummary,
  scheduleTypeLabels,
  timelinessNatureLabels,
  type JobItem,
  type ScheduleApiItem,
} from "./model";

function apiItem(overrides: Partial<ScheduleApiItem> = {}): ScheduleApiItem {
  return {
    schedule_id: "sch-1",
    name: "Hesap mutabakat job'u",
    schedule_type: "INTERVAL",
    timezone_name: "Europe/Istanbul",
    rule_version_ids: ["rv-1"],
    created_by: "user-1",
    local_time: null,
    day_of_week: null,
    day_of_month: null,
    interval_minutes: 10,
    is_active: true,
    next_run_at: "2026-08-17T09:10:00Z",
    created_at: "2026-08-16T12:00:00Z",
    last_triggered_at: null,
    ...overrides,
  };
}

describe("scheduleSummary", () => {
  it("aralıklı tanımı dakika metnine çevirir", () => {
    expect(scheduleSummary(jobFromApi(apiItem({ interval_minutes: 10 })))).toBe("10 dakikada bir");
  });

  it("1 dakikalık aralığı anlık olarak etiketler", () => {
    expect(scheduleSummary(jobFromApi(apiItem({ interval_minutes: 1 })))).toBe(
      "Anlık (1 dakikada bir)",
    );
  });

  it("günlük tanımı saat ile gösterir", () => {
    const item = jobFromApi(
      apiItem({ schedule_type: "DAILY", interval_minutes: null, local_time: "06:00" }),
    );
    expect(scheduleSummary(item)).toBe("Her gün 06:00");
  });

  it("haftalık tanımı gün adı ve saat ile gösterir", () => {
    const item = jobFromApi(
      apiItem({
        schedule_type: "WEEKLY",
        interval_minutes: null,
        local_time: "07:30",
        day_of_week: 2,
      }),
    );
    expect(scheduleSummary(item)).toBe("Haftalık · Çarşamba 07:30");
  });

  it("aylık tanımı gün numarası ve saat ile gösterir", () => {
    const item = jobFromApi(
      apiItem({
        schedule_type: "MONTHLY",
        interval_minutes: null,
        local_time: "08:00",
        day_of_month: 5,
      }),
    );
    expect(scheduleSummary(item)).toBe("Aylık · 5. gün 08:00");
  });

  it("bilinmeyen tür için etikete düşer", () => {
    const item = jobFromApi(apiItem({ schedule_type: "ONCE", interval_minutes: null }));
    expect(scheduleSummary(item)).toBe(scheduleTypeLabels.ONCE);
  });
});

describe("model eşlemeleri", () => {
  it("jobFromApi yılan alanlarını camelCase modele çevirir", () => {
    const item = jobFromApi(apiItem());
    expect(item).toMatchObject({
      id: "sch-1",
      name: "Hesap mutabakat job'u",
      scheduleType: "INTERVAL",
      timezoneName: "Europe/Istanbul",
      ruleVersionIds: ["rv-1"],
      intervalMinutes: 10,
      isActive: true,
      nextRunAt: "2026-08-17T09:10:00Z",
    } satisfies Partial<JobItem>);
  });

  it("jobsFromApi liste yanıtındaki tüm öğeleri eşler", () => {
    const mapped = jobsFromApi({
      api_version: "v1",
      data_origin: "test",
      correlation_id: "c-1",
      items: [apiItem(), apiItem({ schedule_id: "sch-2", name: "İkinci job" })],
    });
    expect(mapped.map((job) => job.id)).toEqual(["sch-1", "sch-2"]);
  });

  it("scheduleProposalsFromApi önerileri camelCase'e çevirir", () => {
    const mapped = scheduleProposalsFromApi({
      api_version: "v1",
      data_origin: "test",
      correlation_id: "c-2",
      dataset_id: "ds-1",
      timeliness_nature: "NEAR_TIME",
      band: "INTERVAL 5-15 dakika",
      proposals: [
        { schedule_type: "INTERVAL", interval_minutes: 5, label: "5 dakikada bir" },
        { schedule_type: "INTERVAL", interval_minutes: 15, label: "15 dakikada bir" },
      ],
    });
    expect(mapped).toEqual([
      { scheduleType: "INTERVAL", intervalMinutes: 5, label: "5 dakikada bir" },
      { scheduleType: "INTERVAL", intervalMinutes: 15, label: "15 dakikada bir" },
    ]);
  });

  it("zamanlılık niteliği etiketleri üç niteliği de kapsar", () => {
    expect(timelinessNatureLabels.NEAR_TIME).toBe("Yakın Zamanlı");
    expect(timelinessNatureLabels.REAL_TIME).toBe("Anlık");
    expect(timelinessNatureLabels.BATCH_TIME).toBe("Toplu (Batch)");
  });
});
