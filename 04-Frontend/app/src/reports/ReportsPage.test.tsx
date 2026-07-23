import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { ReportsPage } from "./ReportsPage";

function renderPage() {
  return render(
    <ThemeModeProvider>
      <MemoryRouter initialEntries={["/reports"]}>
        <ReportsPage />
      </MemoryRouter>
    </ThemeModeProvider>,
  );
}

describe("Raporlar ekranı", () => {
  it("hesaplanan, kısmi, veri yok ve teknik hata sonuçlarını ayrı gösterir", () => {
    renderPage();
    expect(screen.getByRole("heading", { level: 1, name: "Raporlar" })).toBeVisible();
    expect(screen.getAllByTestId("report-icon-slot")).toHaveLength(4);
    expect(screen.getByLabelText("Durum: Hesaplandı")).toBeVisible();
    expect(screen.getByLabelText("Durum: Kısmi")).toBeVisible();
    expect(screen.getByLabelText("Durum: Veri yok")).toBeVisible();
    expect(screen.getByLabelText("Durum: Teknik hata")).toBeVisible();
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(2);
  });

  it("kaynak ve durum filtrelerini uygular ve temizler", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Kaynak ara"), { target: { value: "risk" } });
    expect(screen.getByText("source-risk-mart")).toBeVisible();
    expect(screen.queryByText("source-core-banking")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Filtreleri temizle" }));
    fireEvent.mouseDown(screen.getByLabelText("Sonuç durumu"));
    fireEvent.click(screen.getByRole("option", { name: "Teknik hata" }));
    expect(screen.getByText("source-regulatory-api")).toBeVisible();
    expect(screen.queryByText("source-core-banking")).not.toBeInTheDocument();
  });

  it("yetkisiz durumda filtre veya rapor özeti göstermez", () => {
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <ReportsPage state="unauthorized" />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    expect(screen.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();
    expect(screen.queryByLabelText("Kaynak ara")).not.toBeInTheDocument();
    expect(screen.queryByText("87,10")).not.toBeInTheDocument();
    expect(screen.queryByText("source-core-banking")).not.toBeInTheDocument();
  });
});
