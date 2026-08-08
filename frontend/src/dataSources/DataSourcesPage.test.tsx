import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { DataSourcesPage } from "./DataSourcesPage";
import type { DataSourceListItem } from "./model";

function renderPage(props?: Partial<React.ComponentProps<typeof DataSourcesPage>>) {
  return render(<ThemeModeProvider><MemoryRouter><DataSourcesPage {...props} /></MemoryRouter></ThemeModeProvider>);
}

const item = (overrides: Partial<DataSourceListItem>): DataSourceListItem => ({
  id: "source-a", name: "Kaynak A", sourceType: "POSTGRESQL", status: "TEST_SUCCEEDED",
  availableActions: [], ...overrides,
});

describe("Veri Kaynakları ekranı", () => {
  it("yalnız backend'in verdiği action'ları render eder", () => {
    renderPage({ items: [item({ availableActions: ["TEST_CONNECTION", "REQUEST_ACTIVATION"] })] });
    expect(screen.getByRole("button", { name: "Bağlantıyı test et" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Aktivasyon talep et" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Pasifleştir" })).not.toBeInTheDocument();
  });

  it("karar callback'ini source id değil pending request id ile çağırır", async () => {
    const decide = vi.fn().mockResolvedValue(undefined);
    renderPage({
      items: [item({ availableActions: ["APPROVE_ACTIVATION"], pendingActivationRequestId: "request-a" })],
      onDecideActivation: decide,
    });
    fireEvent.click(screen.getByRole("button", { name: "Onayla" }));
    fireEvent.change(await screen.findByLabelText(/Karar gerekçe kodu/), { target: { value: "VALIDATED" } });
    fireEvent.click(screen.getByRole("button", { name: "Kararı gönder" }));
    await waitFor(() => expect(decide).toHaveBeenCalledWith("request-a", "APPROVE", "VALIDATED"));
  });

  it("pasifleştirme gerekçesi boşken submit'i kapalı tutar", async () => {
    renderPage({ items: [item({ status: "ACTIVE", availableActions: ["PASSIVATE"] })], onPassivate: vi.fn() });
    fireEvent.click(screen.getByRole("button", { name: "Pasifleştir" }));
    expect(screen.getAllByRole("button", { name: "Pasifleştir" }).at(-1)).toBeDisabled();
    fireEvent.change(await screen.findByLabelText(/Gerekçe kodu/), { target: { value: "RETIRED" } });
    expect(screen.getAllByRole("button", { name: "Pasifleştir" }).at(-1)).toBeEnabled();
  });

  it("create formunda owner/username/password yoktur ve secret referansı vardır", () => {
    renderPage({ onCreate: vi.fn() });
    fireEvent.click(screen.getByRole("button", { name: "Yeni veri kaynağı" }));
    expect(screen.getByLabelText(/Secret referansı/)).toBeVisible();
    expect(screen.queryByLabelText(/Sahip kullanıcı/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Kullanıcı adı/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Parola/)).not.toBeInTheDocument();
  });

  it("yetkisiz durumda envanter verisini göstermez", () => {
    renderPage({ state: "unauthorized" });
    expect(screen.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();
    expect(screen.queryByText("Temel Bankacılık")).not.toBeInTheDocument();
  });
});
