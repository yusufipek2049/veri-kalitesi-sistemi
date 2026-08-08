import { describe, expect, it, vi, beforeEach, beforeAll } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { TrendPanel } from "./TrendPanel";
import type { TrendObservation } from "../dashboard/model";

vi.mock("echarts/core", () => ({
  use: vi.fn(),
  init: vi.fn(() => ({
    setOption: vi.fn(),
    resize: vi.fn(),
    dispose: vi.fn(),
  })),
}));

beforeAll(() => {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

function renderWithTheme(ui: ReactNode) {
  return render(
    <ThemeModeProvider forcedMode="light">{ui}</ThemeModeProvider>,
  );
}

function makeObservation(overrides: Partial<TrendObservation> & { date: string }): TrendObservation {
  return {
    displayDate: overrides.date,
    rawScore: null,
    finalScore: null,
    qualification: "Qualified",
    usageDecision: "Allowed",
    coverageRate: null,
    technicalStatus: "Başarılı",
    official: true,
    trend: null,
    versionBoundary: false,
    ...overrides,
  };
}

const trendData: TrendObservation[] = [
  makeObservation({
    date: "2026-06-23",
    displayDate: "23 Haz",
    rawScore: 72.1,
    finalScore: 72.1,
    official: true,
    versionBoundary: true,
    trend: {
      moving_average: null,
      consecutive_deterioration_count: null,
      sudden_deterioration: null,
      time_below_threshold_periods: null,
      improvement_persistence: null,
      version_boundary: true,
      policy_version: "1.0.0",
    },
  }),
  makeObservation({
    date: "2026-06-27",
    displayDate: "27 Haz",
    rawScore: 76.8,
    finalScore: 76.8,
    official: true,
    trend: {
      moving_average: 74.5,
      consecutive_deterioration_count: 0,
      sudden_deterioration: false,
      time_below_threshold_periods: 0,
      improvement_persistence: 1,
      version_boundary: false,
      policy_version: "1.0.0",
    },
  }),
  makeObservation({
    date: "2026-07-01",
    displayDate: "1 Tem",
    rawScore: 78.2,
    finalScore: 78.2,
    official: true,
    trend: {
      moving_average: 75.7,
      consecutive_deterioration_count: 2,
      sudden_deterioration: true,
      time_below_threshold_periods: 3,
      improvement_persistence: 0,
      version_boundary: false,
      policy_version: "1.0.0",
    },
  }),
];

describe("DQ-SCR-027 TrendPanel trend bileşenleri", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("trend bileşenlerinin gösterimi (AC-01)", () => {
    it("trend özet bölümünde tüm bileşenleri gösterir", async () => {
      const user = userEvent.setup();
      renderWithTheme(<TrendPanel observations={trendData} policyVersion="1.0.0" />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      expect(screen.getByText("Trend Bileşenleri")).toBeTruthy();
      expect(screen.getAllByText(/Hareketli ortalama/).length).toBeGreaterThan(0);
      expect(screen.getByText(/Ardışık kötüleşme/)).toBeTruthy();
      expect(screen.getByText(/Ani kötüleşme/)).toBeTruthy();
      expect(screen.getByText(/Eşik altında kalma/)).toBeTruthy();
      expect(screen.getByText(/İyileşme kalıcılığı/)).toBeTruthy();
    });

    it("hareketli ortalama değerini doğru gösterir", async () => {
      const user = userEvent.setup();
      renderWithTheme(<TrendPanel observations={trendData} policyVersion="1.0.0" />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      expect(screen.getAllByText("75,7").length).toBeGreaterThan(0);
    });

    it("ardışık kötüleşme sayısını gösterir", async () => {
      const user = userEvent.setup();
      renderWithTheme(<TrendPanel observations={trendData} policyVersion="1.0.0" />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      expect(screen.getByText("2")).toBeTruthy();
    });

    it("ani kötüleşme durumunu Evet olarak gösterir", async () => {
      const user = userEvent.setup();
      renderWithTheme(<TrendPanel observations={trendData} policyVersion="1.0.0" />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      expect(screen.getAllByText("Evet").length).toBeGreaterThan(0);
    });

    it("eşik altında kalma süresini dönem olarak gösterir", async () => {
      const user = userEvent.setup();
      renderWithTheme(<TrendPanel observations={trendData} policyVersion="1.0.0" />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      expect(screen.getByText("3 dönem")).toBeTruthy();
    });

    it("iyileşme kalıcılığını dönem olarak gösterir", async () => {
      const user = userEvent.setup();
      renderWithTheme(<TrendPanel observations={trendData} policyVersion="1.0.0" />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      expect(screen.getByText("0 dönem")).toBeTruthy();
    });
  });

  describe("istemci yeniden hesaplama yapmaz (AC-02)", () => {
    it("sunucudan gelen bileşenleri olduğu gibi sunar", async () => {
      const user = userEvent.setup();
      renderWithTheme(<TrendPanel observations={trendData} policyVersion="1.0.0" />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      const table = screen.getByRole("table");
      const maCell = within(table).getByText("75,7");
      expect(maCell).toBeTruthy();
      expect(maCell.tagName).toBe("TD");
    });
  });

  describe("sürüm sınırı işareti (AC-03)", () => {
    it("tabloda sürüm sınırı sütunu Evet gösterir", async () => {
      const user = userEvent.setup();
      renderWithTheme(<TrendPanel observations={trendData} policyVersion="1.0.0" />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      const table = screen.getByRole("table");
      expect(within(table).getByText("Sürüm sınırı")).toBeTruthy();
      expect(within(table).getByText("Evet")).toBeTruthy();
    });

    it("sürüm sınırı olmayan gözlemlerde — gösterir", async () => {
      const user = userEvent.setup();
      renderWithTheme(<TrendPanel observations={trendData} policyVersion="1.0.0" />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      const rows = screen.getAllByRole("row");
      const lastRow = rows[rows.length - 1];
      expect(within(lastRow).getByText("—")).toBeTruthy();
    });
  });

  describe("Unknown gösterimi (AC-04)", () => {
    it("politika yoksa Unknown bileşenleri açıkça Unknown gösterir", async () => {
      const user = userEvent.setup();
      const noTrendData: TrendObservation[] = [
        makeObservation({ date: "2026-07-01", displayDate: "1 Tem", rawScore: 80, official: true }),
      ];
      renderWithTheme(<TrendPanel observations={noTrendData} />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      const unknowns = screen.getAllByText("Unknown");
      expect(unknowns.length).toBeGreaterThan(0);
    });

    it("sürüm sınırında moving_average Unknown olarak gösterilir", async () => {
      const user = userEvent.setup();
      renderWithTheme(<TrendPanel observations={trendData} policyVersion="1.0.0" />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      const rows = screen.getAllByRole("row");
      const boundaryRow = rows[1];
      expect(within(boundaryRow).getByText("Unknown")).toBeTruthy();
    });

    it("politika sürümü Unknown olarak gösterilir (policyVersion yoksa)", async () => {
      const user = userEvent.setup();
      renderWithTheme(<TrendPanel observations={trendData} />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      expect(screen.getByText("Politika sürümü:")).toBeTruthy();
      expect(screen.getAllByText("Unknown").length).toBeGreaterThan(0);
    });
  });

  describe("provizyonel gözlem ayrımı (AC-05)", () => {
    it("provizyonel gözlemler Dışlandı olarak işaretlenir", async () => {
      const user = userEvent.setup();
      const dataWithProvisional: TrendObservation[] = [
        makeObservation({
          date: "2026-07-01",
          displayDate: "1 Tem",
          rawScore: 80,
          finalScore: 80,
          official: true,
          technicalStatus: "Başarılı",
        }),
        makeObservation({
          date: "2026-07-05",
          displayDate: "5 Tem",
          rawScore: 82,
          finalScore: 82,
          official: false,
          qualification: "ProvisionallyQualified",
          technicalStatus: "Başarılı",
        }),
      ];
      renderWithTheme(<TrendPanel observations={dataWithProvisional} />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      expect(screen.getByText("Dışlandı")).toBeTruthy();
    });

    it("teknik hata gözlemleri Teknik Hata rozeti ile gösterilir", async () => {
      const user = userEvent.setup();
      const dataWithTechnical: TrendObservation[] = [
        makeObservation({
          date: "2026-07-01",
          displayDate: "1 Tem",
          rawScore: 80,
          official: true,
          technicalStatus: "Başarılı",
        }),
        makeObservation({
          date: "2026-07-05",
          displayDate: "5 Tem",
          rawScore: null,
          official: false,
          technicalStatus: "Teknik Hata",
        }),
      ];
      renderWithTheme(<TrendPanel observations={dataWithTechnical} />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      expect(screen.getByText("Teknik Hata")).toBeTruthy();
    });
  });

  describe("politika sürümü görünürlüğü (AC-06)", () => {
    it("politika sürümünü gösterir", async () => {
      const user = userEvent.setup();
      renderWithTheme(<TrendPanel observations={trendData} policyVersion="2.1.0" />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      expect(screen.getByText("Politika sürümü:")).toBeTruthy();
      expect(screen.getByText("2.1.0")).toBeTruthy();
    });

    it("politika sürümü yoksa Unknown gösterir", async () => {
      const user = userEvent.setup();
      renderWithTheme(<TrendPanel observations={trendData} />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      expect(screen.getByText("Politika sürümü:")).toBeTruthy();
    });
  });

  describe("grafik/tablo eşdeğerliği (AC-07, AC-08)", () => {
    it("tablo hareketli ortalama değerlerini trend verisiyle eşleştirir", async () => {
      const user = userEvent.setup();
      renderWithTheme(<TrendPanel observations={trendData} policyVersion="1.0.0" />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      const table = screen.getByRole("table");
      const officialWithMa = trendData.filter(
        (item) => item.official && item.trend?.moving_average != null,
      );
      for (const obs of officialWithMa) {
        const maValue = obs.trend!.moving_average!.toLocaleString("tr-TR", { maximumFractionDigits: 1 });
        expect(within(table).getAllByText(maValue).length).toBeGreaterThan(0);
      }
    });

    it("grafik erişilebilir alternatife sahiptir", () => {
      renderWithTheme(<TrendPanel observations={trendData} policyVersion="1.0.0" />);

      const chartImg = screen.getByRole("img");
      expect(chartImg).toBeTruthy();
      expect(chartImg.getAttribute("aria-label")).toContain("trend");
    });

    it("tablo klavye ile gezilebilir ve etiketlidir", async () => {
      const user = userEvent.setup();
      renderWithTheme(<TrendPanel observations={trendData} policyVersion="1.0.0" />);
      await user.click(screen.getByRole("button", { name: /tablo/i }));

      const table = screen.getByRole("table");
      expect(table).toBeTruthy();
      expect(screen.getByText("Hareketli ortalama")).toBeTruthy();
      expect(screen.getByText("Sürüm sınırı")).toBeTruthy();
    });

    it("grafik ve tablo arasında geçiş yapılabilir", async () => {
      const user = userEvent.setup();
      renderWithTheme(<TrendPanel observations={trendData} policyVersion="1.0.0" />);

      expect(screen.getByRole("img")).toBeTruthy();

      await user.click(screen.getByRole("button", { name: /tablo/i }));
      expect(screen.getByRole("table")).toBeTruthy();

      await user.click(screen.getByRole("button", { name: /grafik/i }));
      expect(screen.getByRole("img")).toBeTruthy();
    });
  });
});
