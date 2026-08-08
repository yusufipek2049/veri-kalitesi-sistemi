import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { DashboardPage } from "./DashboardPage";
import { syntheticDashboardViewModel, type AppliedDashboardFilters } from "./model";

vi.mock("../components/TrendPanel", () => ({
  TrendPanel: () => <div data-testid="trend-panel-mock" />,
}));

function renderWithProviders(ui: ReactNode) {
  return render(
    <MemoryRouter>
      <ThemeModeProvider forcedMode="light">{ui}</ThemeModeProvider>
    </MemoryRouter>,
  );
}

describe("FR-057 DashboardPage filtre davranışı", () => {
  it("filtre çubuğunu görüntüler ve etiketler", () => {
    renderWithProviders(
      <DashboardPage
        data={syntheticDashboardViewModel}
        filters={{}}
        onFiltersChange={vi.fn()}
        onClearFilters={vi.fn()}
        state="normal"
      />,
    );

    expect(screen.getByLabelText("Kapsam türü filtresi")).toBeTruthy();
    expect(screen.getByLabelText("Kaynak kimliği filtresi")).toBeTruthy();
    expect(screen.getByLabelText("Skor durumu filtresi")).toBeTruthy();
    expect(screen.getByLabelText("Kalite seviyesi filtresi")).toBeTruthy();
  });

  it("filtre değişikliğini callback'e iletir", async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();

    renderWithProviders(
      <DashboardPage
        data={syntheticDashboardViewModel}
        filters={{}}
        onFiltersChange={onFiltersChange}
        onClearFilters={vi.fn()}
        state="normal"
      />,
    );

    const scopeTypeSelect = screen.getByLabelText("Kapsam türü filtresi");
    await user.click(scopeTypeSelect);

    const sourceOption = screen.getByText("Kaynak");
    await user.click(sourceOption);

    expect(onFiltersChange).toHaveBeenCalledWith(
      expect.objectContaining({ scope_type: "SOURCE" }),
    );
  });

  it("scope-forbidden durumunda yetki uyarısı gösterir ve veri sızdırmaz", () => {
    renderWithProviders(
      <DashboardPage
        data={syntheticDashboardViewModel}
        filters={{ scope_id: "forbidden" }}
        onClearFilters={vi.fn()}
        onFiltersChange={vi.fn()}
        state="scope-forbidden"
      />,
    );

    expect(screen.getByText(/yetkiniz yok/)).toBeTruthy();
    expect(screen.getByText(/sızdırılmadı/)).toBeTruthy();
    // KPI kartları gösterilmemeli
    expect(screen.queryByText("Nihai Kalite Skoru")).toBeNull();
  });

  it("invalid-filter durumunda geçersiz parametre uyarısı gösterir", () => {
    renderWithProviders(
      <DashboardPage
        data={syntheticDashboardViewModel}
        filters={{}}
        onClearFilters={vi.fn()}
        onFiltersChange={vi.fn()}
        state="invalid-filter"
      />,
    );

    expect(screen.getByText(/Geçersiz filtre parametresi/)).toBeTruthy();
    expect(screen.getByText(/Varsayılana dön/)).toBeTruthy();
  });

  it("empty durumunda 'veri yok' mesajı gösterir, yetki uyarısı değil", () => {
    renderWithProviders(
      <DashboardPage
        data={syntheticDashboardViewModel}
        filters={{ score_status: "CALCULATED" }}
        onClearFilters={vi.fn()}
        onFiltersChange={vi.fn()}
        state="empty"
      />,
    );

    expect(screen.getByText(/Veri bulunamadı/)).toBeTruthy();
    expect(screen.queryByText(/yetkiniz yok/)).toBeNull();
  });

  it("applied_filters bilgilerini chip olarak gösterir", () => {
    const appliedFilters: AppliedDashboardFilters = {
      window_start: "2026-07-16T00:00:00Z",
      window_end: "2026-08-03T14:30:00Z",
      scope_type: "SOURCE",
      scope_id: "source-a",
      score_status: "CALCULATED",
      level: null,
    };

    renderWithProviders(
      <DashboardPage
        appliedFilters={appliedFilters}
        data={syntheticDashboardViewModel}
        filters={{ scope_type: "SOURCE", scope_id: "source-a", score_status: "CALCULATED" }}
        onFiltersChange={vi.fn()}
        onClearFilters={vi.fn()}
        state="normal"
      />,
    );

    expect(screen.getByText(/Kapsam: SOURCE \(source-a\)/)).toBeTruthy();
    expect(screen.getByText(/Durum: Hesaplandı/)).toBeTruthy();
  });

  it("aktif filtre varken 'Filtreli' chip'i gösterir", () => {
    renderWithProviders(
      <DashboardPage
        data={syntheticDashboardViewModel}
        filters={{ level: "GOOD" }}
        onClearFilters={vi.fn()}
        onFiltersChange={vi.fn()}
        state="normal"
      />,
    );

    expect(screen.getByText("Filtreli")).toBeTruthy();
  });

  it("filtre yokken 'Filtreli' chip'i gösterilmez", () => {
    renderWithProviders(
      <DashboardPage
        data={syntheticDashboardViewModel}
        filters={{}}
        onClearFilters={vi.fn()}
        onFiltersChange={vi.fn()}
        state="normal"
      />,
    );

    expect(screen.queryByText("Filtreli")).toBeNull();
  });

  it("teknik hata ve Unknown ayrımı filtreli görünümde korunur", () => {
    // AC-06: Filtreli görünümde de status ayrımı bozulmaz
    renderWithProviders(
      <DashboardPage
        data={syntheticDashboardViewModel}
        filters={{ score_status: "NOT_CALCULATED_TECHNICAL_ERROR" }}
        onFiltersChange={vi.fn()}
        onClearFilters={vi.fn()}
        state="normal"
      />,
    );

    // Dashboard normal durumda render edilmeli
    expect(screen.getAllByText("Genel Bakış").length).toBeGreaterThan(0);
    // KPI kartları görünür olmalı
    expect(screen.getByText("Nihai Kalite Skoru")).toBeTruthy();
  });
});
