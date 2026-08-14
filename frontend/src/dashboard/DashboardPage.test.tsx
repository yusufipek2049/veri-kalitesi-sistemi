import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as echarts from "echarts/core";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { listCatalogDatasets } from "../catalog/api";
import { fetchDataSources } from "../dataSources/api";
import { fetchScores } from "../scores/api";
import { DashboardApiError, fetchDashboardOverview } from "./api";
import { DashboardPage, TrendTable } from "./DashboardPage";
import type { DashboardOverviewApiResponse, DashboardTrendPeriod } from "./model";

const chart = vi.hoisted(() => ({
  dispose: vi.fn(),
  resize: vi.fn(),
  setOption: vi.fn(),
}));

vi.mock("echarts/core", () => ({
  init: vi.fn(() => chart),
  use: vi.fn(),
}));
vi.mock("./api", async (importOriginal) => ({
  ...await importOriginal<typeof import("./api")>(),
  fetchDashboardOverview: vi.fn(),
}));
vi.mock("../catalog/api", () => ({ listCatalogDatasets: vi.fn() }));
vi.mock("../dataSources/api", () => ({ fetchDataSources: vi.fn() }));
vi.mock("../scores/api", () => ({ fetchScores: vi.fn() }));
vi.mock("../components/NotificationBell", () => ({ NotificationBell: () => null }));

class ResizeObserverMock {
  observe() {}
  disconnect() {}
}

function dashboardFixture(): DashboardOverviewApiResponse {
  const periods = Array.from({ length: 35 }, (_, index) => {
    const start = new Date(Date.UTC(2026, 6, 1 + index));
    const end = new Date(start.getTime() + 86_399_000);
    return {
      period_start: start.toISOString(),
      period_end: end.toISOString(),
      observations: [{
        quality_score_id: `score-${index}`,
        scope_type: "ENTERPRISE",
        scope_id: null,
        score_value: 80,
        score_status: "CALCULATED",
        level: "GOOD",
        calculated_at: end.toISOString(),
        comparison_status: "COMPARABLE",
        comparison_reason_codes: [],
        change: 1,
      }],
    };
  });

  return {
    api_version: "v1",
    data_origin: "test",
    correlation_id: "dashboard-test",
    trend: { as_of: "2026-08-04T12:00:00Z", has_data: true, threshold_value: 63, periods },
    operational_indicators: {
      measurement_qualification: { status: "NO_DATA", evaluated_scope_count: 1, reason_codes: [] },
      technical_errors: { observation_count: 0, execution_count: 0, affected_source_count: 0, last_occurred_at: null },
    },
    role_view: "ADMIN",
  };
}

function renderPage() {
  return render(
    <ThemeModeProvider>
      <MemoryRouter initialEntries={["/dashboard"]}>
        <DashboardPage />
      </MemoryRouter>
    </ThemeModeProvider>,
  );
}

describe("Dashboard dönem seçici", () => {
  beforeEach(() => {
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    vi.mocked(echarts.init).mockImplementation(() => chart as never);
    vi.mocked(fetchDashboardOverview).mockResolvedValue(dashboardFixture());
    vi.mocked(listCatalogDatasets).mockResolvedValue({ api_version: "v1", data_origin: "test", correlation_id: "catalog-test", items: [] });
    vi.mocked(fetchDataSources).mockResolvedValue({ api_version: "v1", data_origin: "test", correlation_id: "sources-test", items: [] });
    vi.mocked(fetchScores).mockResolvedValue({ data_origin: "test", correlation_id: "scores-test", items: [] });
  });

  it("7g, 14g ve 30g seçeneklerini erişilebilir tek seçim grubu olarak render eder", async () => {
    renderPage();

    expect(await screen.findByRole("group", { name: "Trend dönemi" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Son 7 gün" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Son 14 gün" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Son 30 gün" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Aktif dönem: Son 30 gün")).toBeVisible();
  });

  it("seçilen aralığa göre son N dönemi grafiğe verir", async () => {
    renderPage();

    expect(await screen.findByRole("img", { name: "Kalite trend grafiği" })).toHaveAttribute("data-period-count", "30");

    fireEvent.click(screen.getByRole("button", { name: "Son 7 gün" }));
    await waitFor(() => {
      expect(screen.getByRole("img", { name: "Kalite trend grafiği" })).toHaveAttribute("data-period-count", "7");
    });
    expect(screen.getByText("Aktif dönem: Son 7 gün")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Son 14 gün" }));
    await waitFor(() => {
      expect(screen.getByRole("img", { name: "Kalite trend grafiği" })).toHaveAttribute("data-period-count", "14");
    });
  });

  it("grafik render hatasında tablo sekmesini kullanılabilir tutar", async () => {
    vi.mocked(echarts.init).mockImplementationOnce(() => { throw new Error("canvas unavailable"); });
    renderPage();

    expect(await screen.findByText("Grafik görüntülenemedi. Verileri Tablo sekmesinden inceleyebilirsiniz.")).toBeVisible();
    fireEvent.click(screen.getByRole("tab", { name: "Tablo" }));

    expect(screen.getByRole("table", { name: "Kalite trend tablosu" })).toBeVisible();
    expect(screen.getAllByRole("row")).toHaveLength(31);
  });

  it("API'den gelen eşik değerini çizgi ve label yapılandırmasına taşır", async () => {
    renderPage();

    await screen.findByRole("img", { name: "Kalite trend grafiği" });
    const option = chart.setOption.mock.calls.at(-1)?.[0] as {
      series: Array<{ markLine?: { data: Array<{ yAxis?: number; label?: { formatter?: string } }> } }>;
    };
    expect(option.series[0].markLine?.data[0]).toEqual(expect.objectContaining({
      yAxis: 63,
      label: expect.objectContaining({ formatter: "Eşik: 63" }),
    }));
  });

  it("kaynak serilerini eksik dönemlerde null ile tarih eksenine hizalar", async () => {
    const fixture = dashboardFixture();
    fixture.trend.periods[33].observations.push({
      quality_score_id: "source-score-33",
      scope_type: "SOURCE",
      scope_id: "source-a",
      score_value: 71,
      score_status: "CALCULATED",
      level: "ACCEPTABLE",
      calculated_at: fixture.trend.periods[33].period_end,
      comparison_status: "COMPARABLE",
      comparison_reason_codes: [],
      change: null,
    });
    fixture.trend.periods[34].observations.push({
      quality_score_id: "source-score-34",
      scope_type: "SOURCE",
      scope_id: "source-a",
      score_value: 72,
      score_status: "CALCULATED",
      level: "ACCEPTABLE",
      calculated_at: fixture.trend.periods[34].period_end,
      comparison_status: "COMPARABLE",
      comparison_reason_codes: [],
      change: null,
    });
    vi.mocked(fetchDashboardOverview).mockResolvedValueOnce(fixture);

    renderPage();

    await screen.findByRole("img", { name: "Kalite trend grafiği" });
    const option = chart.setOption.mock.calls.at(-1)?.[0] as {
      series: Array<{ id?: string; data: Array<number | null> }>;
    };
    const sourceSeries = option.series.find((item) => item.id === "source:source-a");
    expect(sourceSeries?.data).toHaveLength(30);
    expect(sourceSeries?.data.slice(0, 28)).toEqual(Array(28).fill(null));
    expect(sourceSeries?.data.slice(-2)).toEqual([71, 72]);
  });

  it("trend boş olsa da KPI ve dataset içeriğini göstermeye devam eder", async () => {
    const fixture = dashboardFixture();
    fixture.trend.has_data = false;
    fixture.trend.periods = [];
    vi.mocked(fetchDashboardOverview).mockResolvedValueOnce(fixture);
    vi.mocked(listCatalogDatasets).mockResolvedValueOnce({
      api_version: "v1",
      data_origin: "test",
      correlation_id: "catalog-test",
      items: [{
        dataset_id: "dataset-a",
        data_source_id: "source-a",
        namespace: "public",
        name: "Müşteriler",
        dataset_type: "TABLE",
        status: "ACTIVE",
        estimated_row_count: null,
        field_count: 4,
        version: 1,
      }],
    });

    renderPage();

    expect(await screen.findByText("Henüz trend verisi bulunmuyor. Diğer dashboard verilerini aşağıda inceleyebilirsiniz.")).toBeVisible();
    expect(screen.getByText("Kalite Skoru")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Dataset Kalitesi" })).toBeVisible();
    expect(screen.getByRole("link", { name: "public.Müşteriler" })).toBeVisible();
    expect(screen.queryByText("Henüz dashboard verisi bulunmuyor.")).not.toBeInTheDocument();
  });

  it("filtre toolbar'ını yönetir, API'yi yeniden çağırır ve filtreleri temizler", async () => {
    vi.mocked(fetchDataSources).mockResolvedValue({
      api_version: "v1",
      data_origin: "test",
      correlation_id: "sources-test",
      items: [{
        data_source_id: "source-a",
        name: "Temel Bankacılık",
        source_type: "POSTGRESQL",
        status: "ACTIVE",
        last_test_at: null,
        available_actions: [],
        pending_activation_request_id: null,
        pending_activation_maker_actor_id: null,
        pending_activation_requested_at: null,
        pending_activation_expires_at: null,
        pending_deactivation_request_id: null,
        pending_deactivation_maker_actor_id: null,
        pending_deactivation_requested_at: null,
      }],
    });
    renderPage();

    const toolbar = await screen.findByRole("region", { name: "Dashboard filtreleri" });
    expect(toolbar).toBeVisible();
    fireEvent.change(screen.getByLabelText("Başlangıç tarihi"), { target: { value: "2026-08-01" } });
    await waitFor(() => expect(fetchDashboardOverview).toHaveBeenLastCalledWith(
      expect.objectContaining({ startDate: "2026-08-01" }),
      expect.any(AbortSignal),
    ));
    expect(screen.getByText(/Aktif filtreler: Başlangıç 2026-08-01/)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Filtreleri Temizle" }));
    await waitFor(() => expect(fetchDashboardOverview).toHaveBeenLastCalledWith(
      expect.objectContaining({ startDate: undefined, endDate: undefined, scopeId: undefined }),
      expect.any(AbortSignal),
    ));
    expect(screen.queryByText(/Aktif filtreler:/)).not.toBeInTheDocument();
  });

  it("403 yanıtında önceki veriyi göstermeden yetkisiz yüzeyine geçer", async () => {
    vi.mocked(fetchDashboardOverview).mockRejectedValueOnce(new DashboardApiError("forbidden"));
    renderPage();

    expect(await screen.findByText("Bu sayfayı görüntüleme yetkiniz yok.")).toBeVisible();
    expect(screen.queryByRole("heading", { level: 2, name: "Kalite Trendi" })).not.toBeInTheDocument();
  });
});

function trendPeriod(): DashboardTrendPeriod {
  const node = (scopeType: string, scopeId: string | null) => ({
    qualityScoreId: `score-${scopeType}-${scopeId ?? "enterprise"}`,
    scopeType,
    scopeId,
    scoreValue: scopeType === "ENTERPRISE" ? 82.5 : 75,
    scoreStatus: "CALCULATED" as const,
    level: "GOOD" as const,
    calculatedAt: "2026-08-10T12:00:00Z",
    comparisonStatus: "COMPARABLE" as const,
    comparisonReasonCodes: [],
    change: scopeType === "ENTERPRISE" ? 2.5 : null,
    versionBoundary: false,
    policyVersion: null,
  });
  return {
    periodStart: "2026-08-10T00:00:00Z",
    periodEnd: "2026-08-10T23:59:59Z",
    observations: [node("ENTERPRISE", null), node("SOURCE", "source-a"), node("SOURCE", "source-b")],
  };
}

describe("TrendTable", () => {
  it("dönem ve kurumsal gözlem değerlerini kaynak sayısıyla render eder", () => {
    render(<ThemeModeProvider><TrendTable periods={[trendPeriod()]} sourceNames={new Map()} /></ThemeModeProvider>);

    expect(screen.getByRole("table", { name: "Kalite trend tablosu" })).toBeVisible();
    expect(screen.getAllByRole("columnheader").map((header) => header.textContent)).toEqual([
      "Dönem", "Kurumsal Skor", "Seviye", "Değişim", "Durum", "Kaynak Sayısı",
    ]);
    expect(screen.getByText("10.08.2026")).toBeVisible();
    expect(screen.getByText("82.5")).toBeVisible();
    expect(screen.getByText("+2.5")).toBeVisible();
    expect(screen.getByText("Hesaplandı")).toBeVisible();
    expect(screen.getByRole("cell", { name: "2" })).toBeVisible();
  });

  it("boş durumda erişilebilir tablo yapısını ve açıklamayı korur", () => {
    render(<ThemeModeProvider><TrendTable periods={[]} sourceNames={new Map()} /></ThemeModeProvider>);

    expect(screen.getByRole("table", { name: "Kalite trend tablosu" })).toBeVisible();
    expect(screen.getAllByRole("columnheader")).toHaveLength(6);
    expect(screen.getByText("Henüz trend verisi bulunmuyor.")).toBeVisible();
  });
});
