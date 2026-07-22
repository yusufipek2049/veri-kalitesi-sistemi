import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { RulesPage } from "./RulesPage";

function renderPage() {
  return render(<ThemeModeProvider><MemoryRouter initialEntries={["/rules"]}><RulesPage /></MemoryRouter></ThemeModeProvider>);
}

describe("Kurallar ekranı", () => {
  it("kuralları simetrik ikon yuvaları ve sınıflandırmalarıyla listeler", () => {
    renderPage();
    expect(screen.getByRole("heading", { level: 1, name: "Kurallar" })).toBeVisible();
    expect(screen.getAllByTestId("rule-icon-slot")).toHaveLength(5);
    expect(screen.getAllByLabelText("Durum: Kritik")).toHaveLength(2);
    expect(screen.queryByText("development-maker")).not.toBeInTheDocument();
  });

  it("metin ve kritiklik filtrelerini birlikte uygular", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Kural ara"), { target: { value: "risk" } });
    expect(screen.getByText("Risk skoru geçerlilik aralığı")).toBeVisible();
    expect(screen.queryByText("Müşteri kimliği zorunluluğu")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Kural ara"), { target: { value: "" } });
    fireEvent.mouseDown(screen.getByLabelText("Kritiklik"));
    fireEvent.click(screen.getByRole("option", { name: "Düşük" }));
    expect(screen.getByText("Şube kodu referans bütünlüğü")).toBeVisible();
    expect(screen.queryByText("IBAN tekillik kontrolü")).not.toBeInTheDocument();
  });

  it("yetkisiz durumda filtre veya envanter verisi göstermez", () => {
    render(<ThemeModeProvider><MemoryRouter><RulesPage state="unauthorized" /></MemoryRouter></ThemeModeProvider>);
    expect(screen.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();
    expect(screen.queryByLabelText("Kural ara")).not.toBeInTheDocument();
    expect(screen.queryByText("Müşteri kimliği zorunluluğu")).not.toBeInTheDocument();
  });
});
