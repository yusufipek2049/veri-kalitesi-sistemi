import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

  it("işlem filtresini serbest metin yerine dropdown olarak sunar", () => {
    renderPage();

    fireEvent.mouseDown(screen.getByLabelText("İşlem"));
    fireEvent.click(screen.getByRole("option", { name: "Kural aktivasyonu" }));

    expect(screen.getByRole("combobox", { name: "İşlem" })).toHaveTextContent("Kural aktivasyonu");
    expect(screen.getAllByTestId("audit-icon-slot")).toHaveLength(1);
  });

  it("özel tarih aralığını seçilebilir tarih alanlarıyla sunar", () => {
    const onQuery = vi.fn();
    renderPage({ onQuery });

    fireEvent.mouseDown(screen.getByLabelText("Dönem"));
    fireEvent.click(screen.getByRole("option", { name: "Özel aralık" }));

    expect(screen.getAllByLabelText("Başlangıç tarihi").length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText("Bitiş tarihi").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Uygula" }));
    expect(onQuery).toHaveBeenLastCalledWith(
      expect.objectContaining({
        periodStart: expect.any(String),
        periodEnd: expect.any(String),
      }),
    );
  });

  it("summary kartlarında dağılım, işlemler ve aktörleri gösterir", () => {
    renderPage();

    expect(screen.getByRole("heading", { name: "Sonuç dağılımı" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "En sık işlemler" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "En aktif aktörler" })).toBeVisible();
    expect(screen.getByText("Toplam 6 olay")).toBeVisible();
    expect(screen.getAllByText("synthetic-data-steward").length).toBeGreaterThan(0);
  });

  it("dışa aktarma dialogunda CSV ve JSON formatlarını sunar", () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Dışa Aktar" }));

    expect(screen.getByRole("dialog", { name: "Denetim kayıtlarını dışa aktar" })).toBeVisible();
    fireEvent.mouseDown(screen.getByLabelText("Format"));
    expect(screen.getByRole("option", { name: "CSV" })).toBeVisible();
    expect(screen.getByRole("option", { name: "JSON" })).toBeVisible();
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
    expect(screen.queryByRole("button", { name: "Dışa Aktar" })).not.toBeInTheDocument();
  });

  it("ilişki kodu filtre alanı mevcut ve değiştirilebilir", () => {
    renderPage();

    const correlationInput = screen.getByLabelText("İlişki kodu");
    expect(correlationInput).toBeVisible();
    fireEvent.change(correlationInput, { target: { value: "synthetic-audit-3" } });
    expect(correlationInput).toHaveValue("synthetic-audit-3");
  });

  it("olay satırına tıklanınca detay drawer'i açılır", () => {
    renderPage();

    fireEvent.click(screen.getByText("Kimlik doğrulama"));

    expect(screen.getByText("Olay detayı")).toBeVisible();
    expect(screen.getByText("Aktör ID")).toBeVisible();
  });

  it("drawer'daki ilişkili correlation butonu onQuery'yi tetikler", () => {
    const onQuery = vi.fn();
    renderPage({ onQuery });

    fireEvent.click(screen.getByText("Kimlik doğrulama"));

    fireEvent.click(screen.getByRole("button", { name: "İlişkili correlation olayları" }));
    expect(onQuery).toHaveBeenLastCalledWith(
      expect.objectContaining({ correlationId: expect.any(String) }),
    );
  });

  it("bilinen nesne türlerini yeni sekme linki yapar, yönlendirilemeyen türleri metin bırakır", () => {
    renderPage();

    const ruleLink = screen.getByRole("link", { name: "QualityRule · rule-customer-id-required" });
    const sourceLink = screen.getByRole("link", { name: "DataSource · source-core-banking" });
    const scoringLink = screen.getByRole("link", { name: "ScoringConfiguration · scoring-policy-v2" });
    expect(ruleLink).toHaveAttribute("href", "/rules");
    expect(sourceLink).toHaveAttribute("href", "/data-sources/source-core-banking");
    expect(scoringLink).toHaveAttribute("href", "/scores");
    for (const link of [ruleLink, sourceLink, scoringLink]) {
      expect(link).toHaveAttribute("target", "_blank");
    }
    expect(screen.queryByRole("link", { name: /UserSession/ })).not.toBeInTheDocument();
  });

  it("bütünlük kartından detay drawer'ını açar ve kapatır", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: /Bütünlük doğrulandı/ }));
    expect(screen.getByRole("heading", { name: "Bütünlük doğrulama sonucu" })).toBeVisible();
    expect(screen.getByText("DEVELOPMENT_AUDIT_ACCESS_V1")).toBeVisible();
    expect(screen.getByText("#6")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Bütünlük detayını kapat" }));
    await waitFor(() => expect(screen.queryByRole("heading", { name: "Bütünlük doğrulama sonucu" })).not.toBeInTheDocument());
  });

  it("ilk geçersiz olay aksiyonuyla ilgili olayın detayını açar", () => {
    renderPage({
      page: {
        ...syntheticAuditPage,
        firstInvalidEventId: "audit-3",
        integrityValid: false,
      },
    });

    fireEvent.click(screen.getByRole("button", { name: /Bütünlük sorunu/ }));
    expect(screen.getByText("audit-3")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "İlk geçersiz olayı gör" }));

    expect(screen.getByRole("heading", { name: "Olay detayı" })).toBeVisible();
    expect(screen.getAllByText("Kural aktivasyonu").length).toBeGreaterThan(0);
  });

  it("nesne quick-filter butonuyla objectType ve objectId sorgusunu tetikler", () => {
    const onQuery = vi.fn();
    renderPage({ onQuery });

    fireEvent.click(screen.getByRole("button", {
      name: "DataSource source-core-banking için audit kayıtlarını filtrele",
    }));

    expect(onQuery).toHaveBeenLastCalledWith(expect.objectContaining({
      objectId: "source-core-banking",
      objectType: "DataSource",
    }));
    expect(screen.getByLabelText("Nesne ID")).toHaveValue("source-core-banking");
  });

  it("liste ve timeline görünümleri arasında geçiş yapıp aynı detay drawer'ını açar", () => {
    renderPage();

    expect(screen.getByRole("button", { name: "Liste" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Timeline" }));

    expect(screen.getByRole("heading", { name: "Audit Timeline" })).toBeVisible();
    expect(screen.getByLabelText("Audit olayları zaman çizelgesi")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /LDAP_AUTHENTICATION/ }));
    expect(screen.getByRole("heading", { name: "Olay detayı" })).toBeVisible();
  });

  it("otomatik yenileme seçimini ve yeni olay banner aksiyonunu iletir", () => {
    const onAutoRefreshChange = vi.fn();
    const onNewEventsRefresh = vi.fn();
    renderPage({ newEventCount: 3, onAutoRefreshChange, onNewEventsRefresh });

    fireEvent.mouseDown(screen.getByLabelText("Otomatik yenileme"));
    fireEvent.click(screen.getByRole("option", { name: "30 sn" }));
    expect(onAutoRefreshChange).toHaveBeenCalledWith(30_000);
    expect(screen.getByText("3 yeni olay yüklendi")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Göster" }));
    expect(onNewEventsRefresh).toHaveBeenCalledOnce();
  });
});
