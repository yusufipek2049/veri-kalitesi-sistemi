import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { IssuesPage } from "./IssuesPage";

function renderPage() {
  return render(<ThemeModeProvider><MemoryRouter initialEntries={["/issues"]}><IssuesPage /></MemoryRouter></ThemeModeProvider>);
}

describe("Sorunlar ekranı", () => {
  it("teknik olay, kritik kalite sorunu ve yaşam döngüsü durumlarını ayrı gösterir", () => {
    renderPage();
    expect(screen.getByRole("heading", { level: 1, name: "Sorunlar" })).toBeVisible();
    expect(screen.getAllByTestId("issue-icon-slot")).toHaveLength(8);
    expect(screen.getAllByLabelText("Durum: Kritik")).toHaveLength(2);
    expect(screen.getByLabelText("Durum: Atandı")).toBeVisible();
    expect(screen.getByLabelText("Durum: Doğrulandı")).toBeVisible();
    expect(screen.getAllByText(/Teknik olay/)).toHaveLength(2);
  });

  it("metin, öncelik ve temizleme filtrelerini uygular", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Sorun ara"), { target: { value: "risk" } });
    expect(screen.getByText("DQI-2026-0017")).toBeVisible();
    expect(screen.queryByText("DQI-2026-0018")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Filtreleri temizle" }));
    fireEvent.mouseDown(screen.getByLabelText("Öncelik"));
    fireEvent.click(screen.getByRole("option", { name: "Kritik" }));
    expect(screen.getByText("DQI-2026-0018")).toBeVisible();
    expect(screen.queryByText("DQI-2026-0017")).not.toBeInTheDocument();
  });

  it("yetkisiz durumda filtre veya sorun verisi göstermez", () => {
    render(<ThemeModeProvider><MemoryRouter><IssuesPage state="unauthorized" /></MemoryRouter></ThemeModeProvider>);
    expect(screen.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();
    expect(screen.queryByLabelText("Sorun ara")).not.toBeInTheDocument();
    expect(screen.queryByText("DQI-2026-0018")).not.toBeInTheDocument();
  });

  it("yalnız izinli sorunda incelemeye alma eylemini çalıştırır", async () => {
    const onStartInvestigation = vi.fn().mockResolvedValue(undefined);
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <IssuesPage onStartInvestigation={onStartInvestigation} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "İncelemeye al" }));

    expect(onStartInvestigation).toHaveBeenCalledWith(
      expect.objectContaining({ id: "issue-technical-risk", version: 1 }),
    );
    expect(await screen.findByText("DQI-2026-0017 incelemeye alındı.")).toBeVisible();
  });
});
