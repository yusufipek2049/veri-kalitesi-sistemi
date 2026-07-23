import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { ExecutionsPage } from "./ExecutionsPage";

function renderPage() {
  return render(<ThemeModeProvider><MemoryRouter initialEntries={["/executions"]}><ExecutionsPage /></MemoryRouter></ThemeModeProvider>);
}

describe("Çalıştırmalar ekranı", () => {
  it("teknik hata, kısmi ve başarılı durumları ayrı gösterir", () => {
    renderPage();
    expect(screen.getByRole("heading", { level: 1, name: "Çalıştırmalar" })).toBeVisible();
    expect(screen.getAllByTestId("execution-icon-slot")).toHaveLength(8);
    expect(screen.getByLabelText("Durum: Teknik hata")).toBeVisible();
    expect(screen.getByLabelText("Durum: Kısmi")).toBeVisible();
    expect(screen.getByLabelText("Durum: Tamamlandı")).toBeVisible();
  });

  it("metin ve durum filtrelerini uygular", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Çalıştırma ara"), { target: { value: "timeout" } });
    expect(screen.getByText("execution-timeout")).toBeVisible();
    expect(screen.queryByText("execution-running")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Çalıştırma ara"), { target: { value: "" } });
    fireEvent.mouseDown(screen.getByLabelText("Durum"));
    fireEvent.click(screen.getByRole("option", { name: "Kısmi" }));
    expect(screen.getByText("execution-partial")).toBeVisible();
    expect(screen.queryByText("execution-success")).not.toBeInTheDocument();
  });

  it("yetkisiz durumda filtre veya geçmiş verisi göstermez", () => {
    render(<ThemeModeProvider><MemoryRouter><ExecutionsPage state="unauthorized" /></MemoryRouter></ThemeModeProvider>);
    expect(screen.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();
    expect(screen.queryByLabelText("Çalıştırma ara")).not.toBeInTheDocument();
    expect(screen.queryByText("execution-running")).not.toBeInTheDocument();
  });
});
