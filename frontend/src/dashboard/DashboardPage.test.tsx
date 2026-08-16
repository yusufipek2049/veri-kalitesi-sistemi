import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as echarts from "echarts/core";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { listCatalogDatasets } from "../catalog/api";
import { fetchDataSources } from "../dataSources/api";
import { fetchScoreDetail, fetchScores } from "../scores/api";
import { DashboardApiError, fetchDashboardOverview } from "./api";
import { DashboardPage, DatasetTrendTable } from "./DashboardPage";
import type { DashboardOverviewApiResponse } from "./model";

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
vi.mock("../scores/api", () => ({ fetchScores: vi.fn(), fetchScoreDetail: vi.fn() }));
vi.mock("../components/NotificationBell", () => ({ NotificationBell: () => null }));

class ResizeObserverMock {
  observe() {}
  disconnect() {}
}

const daysAgo = (n: number, hour = 8) => {
  const date = new Date(Date.now() - n * 86_400_000);
  date.setUTCHours(hour, 0, 0, 0);
  return date.toISOString();
};

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

function catalogFixture() {
  return {
    api_version: "v1" as const,
    data_origin: "test",
    correlation_id: "catalog-test",
    items: [
      {
        dataset_id: "dataset-a",
        data_source_id: "source-a",
        namespace: "public",
        name: "Müşteriler",
        dataset_type: "TABLE",
        status: "ACTIVE" as const,
        estimated_row_count: null,
        field_count: 4,
        version: 1,
      },
      {
        dataset_id: "dataset-b",
        data_source_id: "source-a",
        namespace: "public",
        name: "İşlemler",
        dataset_type: "TABLE",
        status: "ACTIVE" as const,
        estimated_row_count: null,
        field_count: 6,
        version: 1,
      },
    ],
  };
}

function scoreItem(datasetId: string, dayOffset: number, value: string) {
  return {
    quality_score_id: `score-${datasetId}-${dayOffset}`,
    execution_id: `exec-${datasetId}-${dayOffset}`,
    scope_type: "DATASET",
    scope_id: datasetId,
    scope_display_name: null,
    scope_parent_name: null,
    score_value: value,
    score_status: "CALCULATED",
    measurement_status: "Passed",
    level: "GOOD",
    policy_version: "SEED_SCORING_V1",
    calculated_at: daysAgo(dayOffset),
    publication_id: "publication-1",
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

describe("Dashboard kalite trendi", () => {
  beforeEach(() => {
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    vi.mocked(echarts.init).mockImplementation(() => chart as never);
    chart.setOption.mockClear();
    vi.mocked(fetchDashboardOverview).mockResolvedValue(dashboardFixture());
    vi.mocked(listCatalogDatasets).mockResolvedValue({ api_version: "v1", data_origin: "test", correlation_id: "catalog-test", items: [] });
    vi.mocked(fetchDataSources).mockResolvedValue({ api_version: "v1", data_origin: "test", correlation_id: "sources-test", items: [] });
    vi.mocked(fetchScores).mockResolvedValue({ data_origin: "test", correlation_id: "scores-test", items: [] });
  });

  it("arama boşken sabit genel ortalamayı gösterir ve dataset serisi eklemez", async () => {
    vi.mocked(listCatalogDatasets).mockResolvedValue(catalogFixture());
    vi.mocked(fetchScores).mockResolvedValue({
      data_origin: "test",
      correlation_id: "scores-test",
      items: [scoreItem("dataset-a", 1, "90.0"), scoreItem("dataset-b", 1, "70.0")],
    });
    renderPage();

    const graph = await screen.findByRole("img", { name: "Kalite trend grafiği" });
    expect(graph).toHaveAttribute("data-has-average-series", "true");
    expect(graph).toHaveAttribute("data-dataset-series-count", "0");
    expect(fetchScores).toHaveBeenCalledWith(
      { scopeType: "DATASET", limit: 200 },
      expect.any(AbortSignal),
    );
    expect(screen.queryByRole("table", { name: "Kalite trend tablosu" })).not.toBeInTheDocument();
    const option = chart.setOption.mock.calls.at(-1)?.[0] as { series: Array<{ data: number[]; name?: string }> };
    expect(option.series.find((item) => item.name === "Genel Ortalama")?.data).toEqual([80]);
  });

  it("arama girildiğinde yalnızca eşleşen datasetleri tablo ve grafiğe taşır", async () => {
    vi.mocked(listCatalogDatasets).mockResolvedValue(catalogFixture());
    vi.mocked(fetchScores).mockResolvedValue({
      data_origin: "test",
      correlation_id: "scores-test",
      items: [
        scoreItem("dataset-a", 2, "88.0"),
        scoreItem("dataset-a", 1, "90.5"),
        scoreItem("dataset-b", 1, "76.0"),
      ],
    });
    renderPage();

    await screen.findByRole("img", { name: "Kalite trend grafiği" });
    fireEvent.change(screen.getByLabelText("Dataset ara"), { target: { value: "müşteriler" } });

    expect(await screen.findByRole("img", { name: "Kalite trend grafiği" })).toHaveAttribute("data-dataset-series-count", "1");
    fireEvent.click(screen.getByRole("tab", { name: "Tablo" }));
    expect(await screen.findByRole("table", { name: "Kalite trend tablosu" })).toBeVisible();
    expect(screen.getByRole("link", { name: "public.Müşteriler" })).toBeVisible();
    expect(screen.queryByText("public.İşlemler")).not.toBeInTheDocument();
    expect(screen.getByText("90.5")).toBeVisible();
  });

  it("hareketli ortalama serisi ve metni içermez", async () => {
    vi.mocked(listCatalogDatasets).mockResolvedValue(catalogFixture());
    vi.mocked(fetchScores).mockResolvedValue({
      data_origin: "test",
      correlation_id: "scores-test",
      items: [scoreItem("dataset-a", 1, "90.0")],
    });
    renderPage();

    await screen.findByRole("img", { name: "Kalite trend grafiği" });
    fireEvent.change(screen.getByLabelText("Dataset ara"), { target: { value: "müşteriler" } });
    await screen.findByRole("img", { name: "Kalite trend grafiği" });

    expect(screen.queryByText(/Hareketli Ortalama/i)).not.toBeInTheDocument();
    const option = chart.setOption.mock.calls.at(-1)?.[0] as { series: Array<{ name?: string }> };
    expect(option.series.some((item) => item.name === "Hareketli Ortalama")).toBe(false);
  });

  it("dönem seçimi dataset geçmiş penceresini daraltır", async () => {
    vi.mocked(listCatalogDatasets).mockResolvedValue(catalogFixture());
    vi.mocked(fetchScores).mockResolvedValue({
      data_origin: "test",
      correlation_id: "scores-test",
      items: [
        scoreItem("dataset-a", 20, "70.0"),
        scoreItem("dataset-a", 2, "90.0"),
      ],
    });
    renderPage();

    await screen.findByRole("img", { name: "Kalite trend grafiği" });
    fireEvent.change(screen.getByLabelText("Dataset ara"), { target: { value: "müşteriler" } });
    expect(await screen.findByRole("img", { name: "Kalite trend grafiği" })).toHaveAttribute("data-day-count", "2");

    fireEvent.click(screen.getByRole("button", { name: "Son 7 gün" }));
    await waitFor(() => {
      expect(screen.getByRole("img", { name: "Kalite trend grafiği" })).toHaveAttribute("data-day-count", "1");
    });
  });

  it("Detaylı Bilgi butonu skorlama parametrelerini modal üzerinde gösterir", async () => {
    vi.mocked(listCatalogDatasets).mockResolvedValue(catalogFixture());
    vi.mocked(fetchScores).mockResolvedValue({
      data_origin: "test",
      correlation_id: "scores-test",
      items: [scoreItem("dataset-a", 1, "92.4")],
    });
    vi.mocked(fetchScoreDetail).mockResolvedValue({
      data_origin: "test",
      correlation_id: "score-detail-test",
      score: scoreItem("dataset-a", 1, "92.4"),
      publication: {
        publication_id: "publication-1",
        execution_id: "exec-dataset-a-1",
        period: "SEED_PERIOD",
        status: "PUBLISHED",
        policy_version: "SEED_SCORING_V1",
        published_at: daysAgo(1, 9),
        superseded_at: null,
      },
      available_actions: [],
      has_contribution_graph: false,
      calculation_details: {
        curve: "logarithmic_improvement",
        parameters: { start: 58, asymptote: 94, window_days: 30 },
      },
      contribution_graph: null,
    });
    renderPage();

    await screen.findByRole("img", { name: "Kalite trend grafiği" });
    fireEvent.change(screen.getByLabelText("Dataset ara"), { target: { value: "müşteriler" } });
    fireEvent.click(await screen.findByRole("tab", { name: "Tablo" }));
    fireEvent.click(await screen.findByRole("button", { name: /Detaylı Bilgi/ }));

    expect(await screen.findByText("Skorlama Detaylı Bilgi")).toBeVisible();
    expect(screen.getByText("Skorlama Parametreleri")).toBeVisible();
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("logarithmic_improvement")).toBeVisible();
    expect(within(dialog).getByText("92.4")).toBeVisible();
    expect(fetchScoreDetail).toHaveBeenCalledWith("score-dataset-a-1", expect.any(AbortSignal));
  });

  it("eşleşme olmayan aramada bilgilendirme gösterir", async () => {
    vi.mocked(listCatalogDatasets).mockResolvedValue(catalogFixture());
    renderPage();

    await screen.findByText("Seçili dönemde ortalama kalite trendi için skor verisi bulunmuyor.");
    fireEvent.change(screen.getByLabelText("Dataset ara"), { target: { value: "olmayan-dataset" } });

    expect(await screen.findByText("Aramayla eşleşen dataset bulunamadı.")).toBeVisible();
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

describe("DatasetTrendTable", () => {
  const row = {
    datasetId: "dataset-a",
    displayName: "public.Müşteriler",
    sourceName: "Temel Kaynak",
    latest: {
      id: "score-1",
      executionId: "exec-1",
      scopeType: "DATASET" as const,
      scopeId: "dataset-a",
      scopeDisplayName: null,
      scopeParentName: null,
      scoreValue: 91.2,
      scoreStatus: "CALCULATED" as const,
      measurementStatus: "Passed",
      level: "GOOD" as const,
      policyVersion: "SEED_SCORING_V1",
      calculatedAt: daysAgo(1),
      publicationId: null,
    },
    points: [{ day: daysAgo(1).slice(0, 10), value: 91.2 }],
  };

  it("dataset satırlarını skor bilgisi ve Detaylı Bilgi butonuyla render eder", () => {
    const onDetail = vi.fn();
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <DatasetTrendTable onDetail={onDetail} rows={[row]} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    expect(screen.getByRole("table", { name: "Kalite trend tablosu" })).toBeVisible();
    expect(screen.getAllByRole("columnheader").map((header) => header.textContent)).toEqual([
      "Dataset", "Kaynak", "Son Skor", "Seviye", "Durum", "Zaman", "Detay",
    ]);
    expect(screen.getByRole("link", { name: "public.Müşteriler" })).toBeVisible();
    expect(screen.getByText("91.2")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /Detaylı Bilgi/ }));
    expect(onDetail).toHaveBeenCalledWith("score-1");
  });

  it("skoru olmayan dataset satırında Detaylı Bilgi butonunu devre dışı tutar", () => {
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <DatasetTrendTable onDetail={vi.fn()} rows={[{ ...row, latest: null }]} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    expect(screen.getByRole("button", { name: /Detaylı Bilgi/ })).toBeDisabled();
    expect(screen.queryByText("Henüz trend verisi bulunmuyor.")).not.toBeInTheDocument();
  });

  it("boş durumda erişilebilir tablo yapısını ve açıklamayı korur", () => {
    render(<ThemeModeProvider><DatasetTrendTable onDetail={vi.fn()} rows={[]} /></ThemeModeProvider>);

    expect(screen.getByRole("table", { name: "Kalite trend tablosu" })).toBeVisible();
    expect(screen.getAllByRole("columnheader")).toHaveLength(7);
    expect(screen.getByText("Henüz trend verisi bulunmuyor.")).toBeVisible();
  });
});
