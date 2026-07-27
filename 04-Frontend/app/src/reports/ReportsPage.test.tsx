import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { ReportsPage } from "./ReportsPage";
import type { ReportItem, ReportRequest, ReportSchedule, ReportScheduleCreateRequest } from "./model";

function renderPage(props?: { reportItems?: ReportItem[]; onCreateReport?: (r: ReportRequest) => Promise<void>; onDownloadReport?: (id: string, name: string) => Promise<void>; onCreateSchedule?: (r: ReportScheduleCreateRequest) => Promise<void>; onDeleteSchedule?: (id: string) => Promise<void> }) {
  return render(
    <ThemeModeProvider>
      <MemoryRouter initialEntries={["/reports"]}>
        <ReportsPage
          onCreateReport={props?.onCreateReport}
          onDownloadReport={props?.onDownloadReport}
          onCreateSchedule={props?.onCreateSchedule}
          onDeleteSchedule={props?.onDeleteSchedule}
          reportItems={props?.reportItems}
        />
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

  it("rapor talep butonu dialog'u açar", () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Rapor Talep Et" }));
    expect(screen.getByText("Rapor Talebi")).toBeVisible();
    expect(screen.getByRole("button", { name: "Raporu Talep Et" })).toBeVisible();
    expect(screen.getByRole("button", { name: "İptal" })).toBeVisible();
  });

  it("rapor talep dialog'u iptal ile kapanır", async () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Rapor Talep Et" }));
    expect(screen.getByRole("dialog", { name: "Rapor Talebi" })).toBeVisible();
    const iptalBtn = screen.getByRole("button", { name: "İptal" });
    fireEvent.click(iptalBtn);
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Rapor Talebi" })).not.toBeInTheDocument();
    });
  });

  it("rapor talep dialog'u onSubmit çağırır", async () => {
    const onCreateReport = vi.fn().mockResolvedValue(undefined);
    renderPage({ onCreateReport });
    fireEvent.click(screen.getByRole("button", { name: "Rapor Talep Et" }));
    fireEvent.click(screen.getByRole("button", { name: "Raporu Talep Et" }));
    await waitFor(() => {
      expect(onCreateReport).toHaveBeenCalledWith(
        expect.objectContaining({
          report_type: "SUMMARY",
          format: "PDF",
          reason_code: "MANUAL_REQUEST",
        }),
      );
    });
  });

  it("rapor geçmişi sekmesi boş durumu gösterir", () => {
    renderPage();
    fireEvent.click(screen.getByText(/Rapor Geçmişi/));
    expect(screen.getByText("Henüz rapor talebiniz bulunmuyor.")).toBeVisible();
  });

  it("rapor geçmişi sekmesinde raporlar listelenir", () => {
    const reportItems: ReportItem[] = [
      {
        report_id: "rpt-1",
        report_type: "SUMMARY",
        format: "PDF",
        status: "READY",
        file_size: 1024,
        expires_at: "2026-07-25T10:00:00Z",
        created_at: "2026-07-24T10:00:00Z",
        completed_at: "2026-07-24T10:05:00Z",
        failure_reason: null,
      },
      {
        report_id: "rpt-2",
        report_type: "DETAIL",
        format: "CSV",
        status: "FAILED",
        file_size: null,
        expires_at: null,
        created_at: "2026-07-24T11:00:00Z",
        completed_at: "2026-07-24T11:01:00Z",
        failure_reason: "Timeout: data too large",
      },
    ];
    renderPage({ reportItems });
    fireEvent.click(screen.getByText(/Rapor Geçmişi/));
    expect(screen.getByText("Özet")).toBeVisible();
    expect(screen.getByText("Detay")).toBeVisible();
    expect(screen.getByText("Başarısız")).toBeVisible();
    expect(screen.getByText("Timeout: data too large")).toBeVisible();
  });

  it("READY rapor için indirme butonu görünür", () => {
    const reportItems: ReportItem[] = [
      {
        report_id: "rpt-1",
        report_type: "SUMMARY",
        format: "PDF",
        status: "READY",
        file_size: 1024,
        expires_at: "2026-07-25T10:00:00Z",
        created_at: "2026-07-24T10:00:00Z",
        completed_at: "2026-07-24T10:05:00Z",
        failure_reason: null,
      },
    ];
    const onDownloadReport = vi.fn().mockResolvedValue(undefined);
    renderPage({ reportItems, onDownloadReport });
    fireEvent.click(screen.getByText(/Rapor Geçmişi/));
    const downloadBtn = screen.getByRole("button", { name: /İndir/ });
    expect(downloadBtn).toBeVisible();
    fireEvent.click(downloadBtn);
    expect(onDownloadReport).toHaveBeenCalledWith("rpt-1", "report-rpt-1.pdf");
  });

  it("QUEUED rapor indirme butonu göstermez", () => {
    const reportItems: ReportItem[] = [
      {
        report_id: "rpt-3",
        report_type: "SUMMARY",
        format: "PDF",
        status: "QUEUED",
        file_size: null,
        expires_at: null,
        created_at: "2026-07-24T12:00:00Z",
        completed_at: null,
        failure_reason: null,
      },
    ];
    renderPage({ reportItems });
    fireEvent.click(screen.getByText(/Rapor Geçmişi/));
    expect(screen.queryByRole("button", { name: /İndir/ })).not.toBeInTheDocument();
  });

  describe("Zamanlanmış Raporlar sekmesi", () => {
    it("boş durumda mesaj gösterir", () => {
      renderPage();
      fireEvent.click(screen.getByText(/Zamanlanmış/));
      expect(screen.getByText("Günlük Özet Raporu")).toBeVisible();
      expect(screen.getByText("Haftalık Detay Raporu")).toBeVisible();
    });

    it("oluşturma dialog'u açar", () => {
      renderPage();
      fireEvent.click(screen.getByText(/Zamanlanmış/));
      fireEvent.click(screen.getByRole("button", { name: "Yeni Zamanlama" }));
      expect(screen.getByText("Zamanlanmış Rapor Oluştur")).toBeVisible();
    });

    it("oluşturma dialog'u iptal ile kapanır", async () => {
      renderPage();
      fireEvent.click(screen.getByText(/Zamanlanmış/));
      fireEvent.click(screen.getByRole("button", { name: "Yeni Zamanlama" }));
      expect(screen.getByRole("dialog", { name: "Zamanlanmış Rapor Oluştur" })).toBeVisible();
      fireEvent.click(screen.getByRole("button", { name: "İptal" }));
      await waitFor(() => {
        expect(screen.queryByRole("dialog", { name: "Zamanlanmış Rapor Oluştur" })).not.toBeInTheDocument();
      });
    });

    it("silme dialog'u açar ve onaylar", async () => {
      const onDeleteSchedule = vi.fn().mockResolvedValue(undefined);
      renderPage({ onDeleteSchedule });
      fireEvent.click(screen.getByText(/Zamanlanmış/));
      const silButtons = screen.getAllByRole("button", { name: "Sil" });
      expect(silButtons.length).toBeGreaterThan(0);
      fireEvent.click(silButtons[0]);
      expect(screen.getByText(/silmek istediğinize emin misiniz/)).toBeVisible();
      fireEvent.click(screen.getByRole("button", { name: "Sil" }));
      await waitFor(() => {
        expect(onDeleteSchedule).toHaveBeenCalled();
      });
    });
  });
});