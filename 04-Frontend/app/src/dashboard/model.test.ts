import { describe, expect, it } from "vitest";
import {
  dashboardViewModelFromApi,
  trendObservations,
  type DashboardSummaryApiResponse,
  type DashboardGovernanceSummary,
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
    expect(viewModel.kpis[0].label).toBe("Ham Kalite Skoru");
    expect(viewModel.kpis[1]).toMatchObject({ value: "İnceleme", statusLabel: "Doğrulama Gerekli" });
    expect(viewModel.kpis[2]).toMatchObject({ value: "—", statusLabel: "Veri Yok" });
    expect(viewModel.kpis[3]).toMatchObject({ value: "0", statusLabel: "Teknik Hata Yok" });
    expect(viewModel.alerts).toEqual([]);
    expect(viewModel.fieldScores).toHaveLength(5);
    expect(viewModel.qualityDimensionRows).toHaveLength(5);
    expect(viewModel.trendObservations).toHaveLength(2);
    expect(viewModel.trendObservations[0].finalScore).toBeNull();
    expect(viewModel.trendObservations[0].technicalStatus).toBe("Hesaplanmadı");
    expect(viewModel.trendObservations[1].rawScore).toBe(87.4);
    expect(viewModel.trendObservations[1].finalScore).toBeNull();
    expect(viewModel.trendObservations[1].official).toBe(false);
    expect(viewModel.comparisonNote).toContain("Unknown");
  });

  it("yalnız uyumlu dönem değişimini iyileşme olarak gösterir", () => {
    const response = apiResponse();
    const latest = response.periods[1].observations[0];
    latest.comparison_status = "COMPARABLE";
    latest.comparison_reason_codes = [];
    latest.change = "2.40";

    const viewModel = dashboardViewModelFromApi(response);

    expect(viewModel.trendObservations[1].official).toBe(true);
    expect(viewModel.comparisonNote).toContain("İyileşme");
    expect(viewModel.comparisonNote).toContain("+2,4");
  });

  it("FR-056 teknik hata göstergesini kalite skorundan ayrı eşler", () => {
    const response = apiResponse();
    response.operational_indicators.measurement_qualification.status = "TECHNICAL_FAILURE";
    response.operational_indicators.technical_errors = {
      observation_count: 3,
      execution_count: 2,
      affected_source_count: 1,
      last_occurred_at: "2026-07-22T10:30:00Z",
    };

    const viewModel = dashboardViewModelFromApi(response);

    expect(viewModel.kpis[1]).toMatchObject({ value: "—", tone: "technical", statusLabel: "Teknik Başarısızlık" });
    expect(viewModel.kpis[3]).toMatchObject({ value: "3", tone: "technical", statusLabel: "Teknik Hata" });
    expect(viewModel.kpis[3].detail).toContain("2 çalıştırma");
  });

  it("DQ-CAP-010 yönetişim profili yoksa governanceNote bağlı değil der", () => {
    const viewModel = dashboardViewModelFromApi(apiResponse());

    expect(viewModel.governanceNote).toContain("bağlı değil");
    expect(viewModel.contributionGraph?.governance).toBeUndefined();
  });

  it("DQ-CAP-010 aktif yönetişim profili governanceNote ve governance özetini taşır", () => {
    const response = apiResponse();
    const governance: DashboardGovernanceSummary = {
      governance_profile_status: "ACTIVE",
      governance_reason_codes: [],
      governance_version: "DQ_ASSET_GOVERNANCE_PROFILE_V1:source-a:4",
      governance_asset_ref: "source-a",
    };
    const observation = response.periods[1].observations[0];
    observation.contribution_graph = {
      ...observation.contribution_graph!,
      governance,
    };

    const viewModel = dashboardViewModelFromApi(response);

    expect(viewModel.governanceNote).toContain("etkin");
    expect(viewModel.governanceNote).toContain("DQ_ASSET_GOVERNANCE_PROFILE_V1:source-a:4");
    expect(viewModel.contributionGraph?.governance).toEqual(governance);
  });

  it("DQ-CAP-010 belirsiz yönetişim profili governanceNote'da reason codes gösterir", () => {
    const response = apiResponse();
    const governance: DashboardGovernanceSummary = {
      governance_profile_status: "AMBIGUOUS_EFFECTIVITY",
      governance_reason_codes: ["OVERLAPPING_EFFECTIVITY_RANGE"],
      governance_version: null,
      governance_asset_ref: null,
    };
    const observation = response.periods[1].observations[0];
    observation.contribution_graph = {
      ...observation.contribution_graph!,
      governance,
    };

    const viewModel = dashboardViewModelFromApi(response);

    expect(viewModel.governanceNote).toContain("uygulanmadı");
    expect(viewModel.governanceNote).toContain("AMBIGUOUS_EFFECTIVITY");
    expect(viewModel.governanceNote).toContain("OVERLAPPING_EFFECTIVITY_RANGE");
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
            comparison_status: "UNKNOWN",
            comparison_reason_codes: ["NO_PREVIOUS_OBSERVATION"],
            change: null,
            contribution_graph: {
              graph_version: "DQ_SCORE_CONTRIBUTION_GRAPH_V1",
              official: true,
              measurement_qualification: "UNKNOWN",
              critical_rule_status: "UNKNOWN",
              critical_asset_status: "UNKNOWN",
              coverage_status: "UNKNOWN",
              risk_status: "UNKNOWN",
              sla_status: "UNKNOWN",
              usage_decision: "UNKNOWN",
            },
          },
        ],
      },
    ],
    operational_indicators: {
      measurement_qualification: {
        status: "VALIDATION_REQUIRED",
        evaluated_scope_count: 1,
        reason_codes: ["QUALIFICATION_POLICY_UNAVAILABLE"],
        policy_version: null,
      },
      critical_controls: {
        status: "NOT_AVAILABLE",
        reason_code: "CRITICAL_RULE_RESULT_NOT_AVAILABLE",
        passed_count: null,
        failed_count: null,
        not_evaluated_count: null,
      },
      technical_errors: {
        observation_count: 0,
        execution_count: 0,
        affected_source_count: 0,
        last_occurred_at: null,
      },
    },
    role_view: "EXECUTIVE",
  };
}
