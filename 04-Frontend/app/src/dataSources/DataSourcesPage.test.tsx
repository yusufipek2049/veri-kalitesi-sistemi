import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { DataSourcesPage } from "./DataSourcesPage";

function renderPage() {
  return render(<ThemeModeProvider><MemoryRouter initialEntries={["/data-sources"]}><DataSourcesPage /></MemoryRouter></ThemeModeProvider>);
}

describe("Veri Kaynakları ekranı", () => {
  it("kaynakları simetrik ikon yuvaları ve durumlarıyla listeler", () => {
    renderPage();

    expect(screen.getByRole("heading", { level: 1, name: "Veri Kaynakları" })).toBeVisible();
    expect(screen.getAllByTestId("source-icon-slot")).toHaveLength(4);
    expect(screen.getByLabelText("Durum: Aktif")).toBeVisible();
    expect(screen.queryByText("development-reference-only")).not.toBeInTheDocument();
  });

  it("metin filtresini uygular ve temizlenebilir tutar", () => {
    renderPage();
    const search = screen.getByLabelText("Kaynak ara");

    fireEvent.change(search, { target: { value: "risk" } });
    expect(screen.getByText("Risk Veri Martı")).toBeVisible();
    expect(screen.queryByText("Temel Bankacılık")).not.toBeInTheDocument();

    fireEvent.change(search, { target: { value: "" } });
    expect(screen.getByText("Temel Bankacılık")).toBeVisible();
  });

  it("yetkisiz durumda envanter verisi göstermez", () => {
    render(<ThemeModeProvider><MemoryRouter><DataSourcesPage state="unauthorized" /></MemoryRouter></ThemeModeProvider>);
    expect(screen.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();
    expect(screen.queryByText("Temel Bankacılık")).not.toBeInTheDocument();
  });
});
