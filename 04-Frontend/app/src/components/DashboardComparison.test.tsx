import { render, screen, within } from "@testing-library/react";
import { ThemeProvider } from "@mui/material/styles";
import { describe, expect, it } from "vitest";
import {
  syntheticFieldScores,
  syntheticQualityDimensionRows,
} from "../dashboard/model";
import { appTheme } from "../theme/theme";
import { FieldScoreComparison } from "./FieldScoreComparison";
import { QualityDimensionMatrix } from "./QualityDimensionMatrix";

describe("dashboard karşılaştırma panelleri", () => {
  it("FR-054 veri alanı skorlarını renk dışı erişilebilir değerlerle sunar", () => {
    render(
      <ThemeProvider theme={appTheme}>
        <FieldScoreComparison items={syntheticFieldScores} />
      </ThemeProvider>,
    );

    expect(screen.getAllByRole("progressbar")).toHaveLength(5);
    expect(screen.getByRole("progressbar", { name: /Finans: 94,2 puan, İyi/ })).toHaveAttribute("aria-valuenow", "94.2");
    expect(screen.getByText("68,7")).toBeVisible();
  });

  it("FR-058 kalite boyutu görselini aynı değerleri taşıyan tablo olarak sunar", () => {
    render(
      <ThemeProvider theme={appTheme}>
        <QualityDimensionMatrix rows={syntheticQualityDimensionRows} />
      </ThemeProvider>,
    );

    const table = screen.getByRole("table", { name: "Sentetik kalite boyutu matrisi" });
    expect(within(table).getAllByRole("row")).toHaveLength(6);
    expect(within(table).getByLabelText("Operasyon, Güncellik: Hesaplanmadı, Hesaplanmadı")).toHaveTextContent("—");
    expect(within(table).getByLabelText("Referans, Doğruluk: 66, Kritik")).toHaveTextContent("66");
  });

  it("veri sağlanmadığında sıfır üretmez", () => {
    render(
      <ThemeProvider theme={appTheme}>
        <FieldScoreComparison items={[]} />
        <QualityDimensionMatrix rows={[]} />
      </ThemeProvider>,
    );

    expect(screen.getByText("Karşılaştırma verisi bu API kapsamında sağlanmıyor.")).toBeVisible();
    expect(screen.getByText("Boyut matrisi bu API kapsamında sağlanmıyor.")).toBeVisible();
  });
});
