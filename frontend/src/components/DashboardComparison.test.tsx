import { fireEvent, render, screen, within } from "@testing-library/react";
import { ThemeProvider } from "@mui/material/styles";
import { beforeAll, describe, expect, it, vi } from "vitest";
import {
  syntheticFieldScores,
  syntheticQualityDimensionRows,
  type FieldScoreViewModel,
} from "../dashboard/model";
import { appTheme } from "../theme/theme";
import { FieldScoreComparison } from "./FieldScoreComparison";
import { QualityDimensionMatrix } from "./QualityDimensionMatrix";
import { ScoreContributionPanel } from "./ScoreContributionPanel";

/**
 * echarts zrender jsdom'da canvas 2d bağlamı bulamaz.
 * Test ortamında setOption çökmesini önlemek için boş bağlam sağlanır.
 */
beforeAll(() => {
  if (typeof globalThis.ResizeObserver === "undefined") {
    (globalThis as Record<string, unknown>).ResizeObserver = class {
      observe() { /* noop */ }
      unobserve() { /* noop */ }
      disconnect() { /* noop */ }
    };
  }
  const ctx: Record<string, unknown> = {};
  const noop = () => undefined;
  const methods = [
    "save", "restore", "scale", "translate", "rotate", "transform",
    "setTransform", "resetTransform", "createLinearGradient",
    "createRadialGradient", "createPattern", "clearRect", "fillRect",
    "strokeRect", "beginPath", "closePath", "moveTo", "lineTo",
    "bezierCurveTo", "quadraticCurveTo", "arc", "arcTo", "rect",
    "ellipse", "fill", "stroke", "clip", "fillText", "strokeText",
    "getImageData", "putImageData", "drawImage",
    "setLineDash", "getLineDash", "createImageData", "isPointInPath",
    "isPointInStroke",
  ];
  for (const m of methods) ctx[m] = noop;
  ctx.measureText = () => ({ width: 0 });
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(ctx as unknown as CanvasRenderingContext2D);
});

function renderWithTheme(ui: React.ReactElement) {
  return render(<ThemeProvider theme={appTheme}>{ui}</ThemeProvider>);
}

function mockClipboard() {
  if (!navigator.clipboard) {
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn() },
      writable: true,
      configurable: true,
    });
  }
  return vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);
}

describe("dashboard karşılaştırma panelleri", () => {
  it("FR-054 veri alanı skorlarını renk dışı erişilebilir değerlerle sunar", () => {
    renderWithTheme(<FieldScoreComparison items={syntheticFieldScores} />);

    expect(screen.getAllByRole("progressbar")).toHaveLength(5);
    expect(screen.getByRole("progressbar", { name: /Finans: 94,2 puan, İyi/ })).toHaveAttribute("aria-valuenow", "94.2");
    expect(screen.getByText("68,7")).toBeVisible();
  });

  it("FR-058 kalite boyutu görselini aynı değerleri taşıyan tablo olarak sunar", () => {
    renderWithTheme(<QualityDimensionMatrix rows={syntheticQualityDimensionRows} />);

    const table = screen.getByRole("table", { name: "Sentetik kalite boyutu matrisi" });
    expect(within(table).getAllByRole("row")).toHaveLength(6);
    expect(within(table).getByLabelText("Operasyon, Güncellik: Hesaplanmadı, Hesaplanmadı")).toHaveTextContent("—");
    expect(within(table).getByLabelText("Referans, Doğruluk: 66, Kritik")).toHaveTextContent("66");
  });

  it("veri sağlanmadığında sıfır üretmez", () => {
    renderWithTheme(
      <>
        <FieldScoreComparison items={[]} />
        <QualityDimensionMatrix rows={[]} />
      </>,
    );

    expect(screen.getByText("Karşılaştırma verisi bu API kapsamında sağlanmıyor.")).toBeVisible();
    expect(screen.getByText("Boyut matrisi bu API kapsamında sağlanmıyor.")).toBeVisible();
  });

  describe("FR-058 FieldScoreComparison görünüm geçişi", () => {
    it("varsayılan grafik görünümünde ilerleme çubukları gösterir", () => {
      renderWithTheme(<FieldScoreComparison items={syntheticFieldScores} />);
      expect(screen.getAllByRole("progressbar")).toHaveLength(5);
      expect(screen.queryByRole("table")).toBeNull();
    });

    it("tablo görünümüne geçildiğinde aynı verileri tablo olarak gösterir (AC-01)", () => {
      renderWithTheme(<FieldScoreComparison items={syntheticFieldScores} />);
      fireEvent.click(screen.getByRole("button", { name: /^Tablo$/ }));

      const table = screen.getByRole("table", { name: "Veri alanı bazlı skorlar tablosu" });
      expect(within(table).getAllByRole("row")).toHaveLength(6);
      expect(within(table).getByText("Finans")).toBeVisible();
      expect(within(table).getByText("94,2")).toBeVisible();
      expect(screen.queryByRole("progressbar")).toBeNull();
    });

    it("grafik ve tablo aynı view model'den türetilir; skorlar eşit (AC-02)", () => {
      renderWithTheme(<FieldScoreComparison items={syntheticFieldScores} />);

      const chartScores = screen.getAllByRole("progressbar").map((el) =>
        el.getAttribute("aria-valuenow"),
      );

      fireEvent.click(screen.getByRole("button", { name: /^Tablo$/ }));
      const table = screen.getByRole("table");
      const tableCells = within(table).getAllByRole("cell").filter(
        (el) => el.textContent !== null && /^\d/.test(el.textContent!),
      );

      expect(tableCells).toHaveLength(syntheticFieldScores.length);
      syntheticFieldScores.forEach((item, i) => {
        expect(chartScores[i]).toBe(String(item.score));
      });
    });

    it("Unknown/provizyonel durumlar tabloda ayırt edilir (AC-04)", () => {
      const items: FieldScoreViewModel[] = [
        { id: "f1", label: "Alan A", score: null, tone: "unknown", statusLabel: "Hesaplanmadı" },
        { id: "f2", label: "Alan B", score: 72, tone: "warning", statusLabel: "Sınırlı Kapsam" },
      ];
      renderWithTheme(<FieldScoreComparison items={items} />);
      fireEvent.click(screen.getByRole("button", { name: /^Tablo$/ }));

      const table = screen.getByRole("table");
      expect(within(table).getByText("Hesaplanmadı")).toBeVisible();
      expect(within(table).getByText("Sınırlı Kapsam")).toBeVisible();
      expect(within(table).getAllByText("—").length).toBeGreaterThanOrEqual(1);
    });

    it("dışa aktarım tablo içeriğini panoya kopyalar (AC-03)", async () => {
      const spy = mockClipboard();
      renderWithTheme(<FieldScoreComparison items={syntheticFieldScores} />);
      fireEvent.click(screen.getByRole("button", { name: /^Tablo$/ }));
      fireEvent.click(screen.getByRole("button", { name: "Tabloyu kopyala" }));

      await vi.waitFor(() => expect(spy).toHaveBeenCalled());
      const text = spy.mock.calls[0][0] as string;
      expect(text).toContain("Finans");
      expect(text).toContain("94,2");
      expect(text).toContain("İyi");
      spy.mockRestore();
    });
  });

  describe("FR-058 QualityDimensionMatrix görünüm geçişi", () => {
    it("varsayılan tablo görünümünde matrisi gösterir", () => {
      renderWithTheme(<QualityDimensionMatrix rows={syntheticQualityDimensionRows} />);
      expect(screen.getByRole("table", { name: "Sentetik kalite boyutu matrisi" })).toBeVisible();
    });

    it("grafik görünümüne geçildiğinde grafik gösterilir (AC-01)", () => {
      renderWithTheme(<QualityDimensionMatrix rows={syntheticQualityDimensionRows} />);
      fireEvent.click(screen.getByRole("button", { name: /^Grafik$/ }));

      expect(screen.getByRole("img", { name: /Kalite boyutu matrisi grafiği/ })).toBeVisible();
      expect(screen.queryByRole("table")).toBeNull();
    });

    it("Unknown/provizyonel durumlar tabloda korunur (AC-04)", () => {
      renderWithTheme(<QualityDimensionMatrix rows={syntheticQualityDimensionRows} />);
      const table = screen.getByRole("table");
      const unknownCells = within(table).getAllByText("—");
      expect(unknownCells.length).toBeGreaterThanOrEqual(1);
      expect(unknownCells[0]).toBeVisible();
    });

    it("dışa aktarım matris verisini panoya kopyalar (AC-03)", async () => {
      const spy = mockClipboard();
      renderWithTheme(<QualityDimensionMatrix rows={syntheticQualityDimensionRows} />);
      fireEvent.click(screen.getByRole("button", { name: "Tabloyu kopyala" }));

      await vi.waitFor(() => expect(spy).toHaveBeenCalled());
      const text = spy.mock.calls[0][0] as string;
      expect(text).toContain("Finans");
      expect(text).toContain("Tamlık");
      expect(text).toContain("96");
      spy.mockRestore();
    });
  });

  describe("FR-058 ScoreContributionPanel görünüm geçişi", () => {
    const mockComponents = [
      { component_ref: "dim-completeness", component_type: "DIMENSION" as const, included: true, weight: "0.3", contribution: "0.15", exclusion_reason: null },
      { component_ref: "dim-accuracy", component_type: "DIMENSION" as const, included: true, weight: "0.25", contribution: "0.12", exclusion_reason: null },
      { component_ref: "rule-x", component_type: "RULE" as const, included: false, weight: null, contribution: null, exclusion_reason: "NOT_EVALUATED" },
    ];

    it("varsayılan grafik görünümünde grafik gösterir", () => {
      renderWithTheme(<ScoreContributionPanel components={mockComponents} />);
      expect(screen.getByRole("img", { name: /Skor katkı grafiği/ })).toBeVisible();
    });

    it("tablo görünümüne geçildiğinde tüm bileşenleri gösterir (AC-01)", () => {
      renderWithTheme(<ScoreContributionPanel components={mockComponents} />);
      fireEvent.click(screen.getByRole("button", { name: /^Tablo$/ }));

      const table = screen.getByRole("table", { name: "Skor katkı tablosu" });
      expect(within(table).getAllByRole("row")).toHaveLength(4);
      expect(within(table).getByText("dim-completeness")).toBeVisible();
      expect(within(table).getByText("rule-x")).toBeVisible();
      expect(within(table).getByText("NOT_EVALUATED")).toBeVisible();
    });

    it("bilinmeyen durumlar tabloda '—' olarak korunur (AC-04)", () => {
      renderWithTheme(<ScoreContributionPanel />);
      expect(screen.getByText(/Katkı kanıtı Unknown/)).toBeVisible();
    });

    it("dışa aktarım katkı verilerini panoya kopyalar (AC-03)", async () => {
      const spy = mockClipboard();
      renderWithTheme(<ScoreContributionPanel components={mockComponents} />);
      fireEvent.click(screen.getByRole("button", { name: /^Tablo$/ }));
      fireEvent.click(screen.getByRole("button", { name: "Tabloyu kopyala" }));

      await vi.waitFor(() => expect(spy).toHaveBeenCalled());
      const text = spy.mock.calls[0][0] as string;
      expect(text).toContain("dim-completeness");
      expect(text).toContain("DIMENSION");
      expect(text).toContain("NOT_EVALUATED");
      spy.mockRestore();
    });
  });
});
