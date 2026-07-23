import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { AuditPage } from "./AuditPage";
import { syntheticAuditPage } from "./model";

function renderPage(props: React.ComponentProps<typeof AuditPage> = {}) {
  return render(
    <ThemeModeProvider>
      <MemoryRouter initialEntries={["/audit"]}>
        <AuditPage {...props} />
      </MemoryRouter>
    </ThemeModeProvider>,
  );
}

describe("Denetim ekranı", () => {
  it("başarılı, başarısız ve reddedilen olayları bütünlük özetiyle gösterir", () => {
    renderPage();

    expect(screen.getByRole("heading", { level: 1, name: "Denetim" })).toBeVisible();
    expect(screen.getAllByTestId("audit-icon-slot")).toHaveLength(6);
    expect(screen.getAllByText("Başarılı")).toHaveLength(4);
    expect(screen.getByText("Başarısız")).toBeVisible();
    expect(screen.getByText("Reddedildi")).toBeVisible();
    expect(screen.getByText("Bütünlük doğrulandı")).toBeVisible();
  });

  it("aktör ve sonuç filtrelerini uygular ve temizler", () => {
    const onQuery = vi.fn();
    renderPage({ onQuery });

    fireEvent.change(screen.getByLabelText("Aktör"), {
      target: { value: "rule-checker" },
    });
    expect(screen.getByText("Kural aktivasyonu")).toBeVisible();
    expect(screen.queryByText("Bağlantı testi")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Filtreleri temizle" }));
    expect(onQuery).toHaveBeenLastCalledWith(
      expect.objectContaining({ actorId: "", result: "ALL" }),
    );
    fireEvent.mouseDown(screen.getByLabelText("Sonuç"));
    fireEvent.click(screen.getByRole("option", { name: "Reddedildi" }));
    expect(screen.getByText("Skor politikası aktivasyonu")).toBeVisible();
    expect(screen.queryByText("Kural aktivasyonu")).not.toBeInTheDocument();
  });

  it("bütünlük hatasını görünür ve yüksek öncelikli gösterir", () => {
    renderPage({ page: { ...syntheticAuditPage, integrityValid: false } });

    expect(screen.getByText("Bütünlük sorunu")).toBeVisible();
    expect(
      screen.getByText("Audit zinciri bütünlük kontrolünden geçmedi"),
    ).toBeVisible();
  });

  it("yetkisiz durumda filtre veya audit verisi göstermez", () => {
    renderPage({ state: "unauthorized" });

    expect(screen.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();
    expect(screen.queryByLabelText("Aktör")).not.toBeInTheDocument();
    expect(screen.queryByText("Kural aktivasyonu")).not.toBeInTheDocument();
    expect(screen.queryByText("Bütünlük doğrulandı")).not.toBeInTheDocument();
  });
});
