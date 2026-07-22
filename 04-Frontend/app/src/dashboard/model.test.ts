import { describe, expect, it } from "vitest";
import {
  dashboardViewModelFromApi,
  trendObservations,
  type DashboardSummaryApiResponse,
} from "./model";

describe("dashboard trend modeli", () => {
  it("provizyonel ve teknik sonuçları resmî trendden dışlar", () => {
    const official = trendObservations.filter((item) => item.official);

    expect(official).toHaveLength(6);
    expect(official.every((item) => item.technicalStatus !== "Teknik Hata")).toBe(true);
    expect(official.some((item) => item.qualification === "ProvisionallyQualified")).toBe(false);
  });

  it("teknik hatayı sıfır skor olarak üretmez", () => {
    const technicalFailure = trendObservations.find((item) => item.technicalStatus === "Teknik Hata");

    expect(technicalFailure?.rawScore).toBeNull();
    expect(technicalFailure?.finalScore).toBeNull();
  });

  it("FR-054 API özetini eksik alan uydurmadan view-model'e dönüştürür", () => {
    const viewModel = dashboardViewModelFromApi(apiResponse());

    expect(viewModel.kpis[0].value).toBe("87,4");
    expect(viewModel.kpis[1]).toMatchObject({ value: "—", statusLabel: "Veri Yok" });
    expect(viewModel.alerts).toEqual([]);
    expect(viewModel.trendObservations).toHaveLength(2);
    expect(viewModel.trendObservations[0].finalScore).toBeNull();
    expect(viewModel.trendObservations[0].technicalStatus).toBe("Hesaplanmadı");
    expect(viewModel.trendObservations[1].official).toBe(true);
  });
});

function apiResponse(): DashboardSummaryApiResponse {
  return {
    api_version: "v1",
    data_origin: "synthetic-development",
    correlation_id: "correlation-test",
    as_of: "2026-07-22T12:00:00Z",
    has_data: true,
    periods: [
      {
        period_start: "2026-07-21T00:00:00Z",
        period_end: "2026-07-22T00:00:00Z",
        observations: [],
      },
      {
        period_start: "2026-07-22T00:00:00Z",
        period_end: "2026-07-23T00:00:00Z",
        observations: [
          {
            quality_score_id: "synthetic-score",
            scope_type: "ENTERPRISE",
            scope_id: null,
            score_value: "87.40",
            score_status: "CALCULATED",
            level: "ACCEPTABLE",
            calculated_at: "2026-07-22T11:00:00Z",
          },
        ],
      },
    ],
  };
}
