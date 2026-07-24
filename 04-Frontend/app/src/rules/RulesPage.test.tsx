import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { RulesPage } from "./RulesPage";
import type { RuleListItem, RuleTestResult } from "./model";

function renderPage() {
  return render(<ThemeModeProvider><MemoryRouter initialEntries={["/rules"]}><RulesPage /></MemoryRouter></ThemeModeProvider>);
}

function openMenu(itemIndex: number) {
  const triggers = screen.getAllByTestId("rule-actions-trigger");
  fireEvent.click(triggers[itemIndex]);
}

function clickMenuItem(label: string) {
  fireEvent.click(screen.getByText(label));
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

  it("her satırda eylem menüsü gösterir", () => {
    renderPage();
    expect(screen.getAllByTestId("rule-actions-trigger")).toHaveLength(5);
  });

  it("eylem menüsünde kullanılabilir eylemleri listeler", () => {
    renderPage();
    openMenu(0);
    expect(screen.getByText("Sürüm Oluştur")).toBeVisible();
    expect(screen.getByText("Pasifleştir")).toBeVisible();
    expect(screen.queryByText("Test Et")).not.toBeInTheDocument();
  });

  it("kullanılabilir eylemi olmayan satırda bilgi mesajı gösterir", () => {
    const items: RuleListItem[] = [{
      id: "rule-no-actions", code: "NO_ACTIONS", name: "Eylemsiz Kural", datasetId: "ds-1",
      dimension: "COMPLETENESS", status: "PASSIVE", versionId: "rv-1", versionNo: 1,
      ruleType: "REQUIRED", criticality: "LOW", createdAt: "2026-07-24T10:00:00Z",
      availableActions: [], version: 1,
    }];
    render(<ThemeModeProvider><MemoryRouter><RulesPage items={items} /></MemoryRouter></ThemeModeProvider>);
    openMenu(0);
    expect(screen.getByText("Kullanılabilir eylem yok")).toBeVisible();
  });
});

describe("Kural mutasyon dialog'ları", () => {
  it("sürüm oluşturma dialogunu açar", async () => {
    const onVersion = vi.fn();
    const items: RuleListItem[] = [{
      id: "rule-1", code: "TEST", name: "Test Kuralı", datasetId: "ds-1",
      dimension: "COMPLETENESS", status: "DRAFT", versionId: "rv-1", versionNo: 1,
      ruleType: "REQUIRED", criticality: "MEDIUM", createdAt: "2026-07-24T10:00:00Z",
      availableActions: ["CREATE_VERSION"], version: 1,
    }];
    render(<ThemeModeProvider><MemoryRouter><RulesPage items={items} onCreateVersion={onVersion} /></MemoryRouter></ThemeModeProvider>);
    openMenu(0);
    clickMenuItem("Sürüm Oluştur");
    expect(screen.getByText("Yeni Sürüm Oluştur — Test Kuralı")).toBeVisible();
    expect(screen.getByDisplayValue("100")).toBeVisible();
    // Dialog kapatma
    await act(async () => {
      fireEvent.click(screen.getByText("İptal"));
    });
    await vi.waitFor(() => {
      expect(screen.queryByText("Yeni Sürüm Oluştur — Test Kuralı")).not.toBeInTheDocument();
    });
  });

  it("test sonucu dialogunu açar ve sonuçları gösterir", async () => {
    const testResult: RuleTestResult = {
      rule_test_result_id: "tr-1", rule_version_id: "rv-1", status: "SUCCESS",
      record_limit: 10000, checked_count: 1000, passed_count: 950, failed_count: 50,
      not_evaluated_count: 0, success_rate: 95.0, preview_score: 95.0,
      official_score_included: false, error_class: null, message: "Test başarılı",
      created_at: "2026-07-24T10:00:00Z",
    };
    const onTest = vi.fn().mockResolvedValue(testResult);
    const items: RuleListItem[] = [{
      id: "rule-1", code: "TEST", name: "Test Kuralı", datasetId: "ds-1",
      dimension: "COMPLETENESS", status: "DRAFT", versionId: "rv-1", versionNo: 1,
      ruleType: "REQUIRED", criticality: "MEDIUM", createdAt: "2026-07-24T10:00:00Z",
      availableActions: ["TEST_RULE"], version: 1,
    }];
    render(<ThemeModeProvider><MemoryRouter><RulesPage items={items} onTestRule={onTest} /></MemoryRouter></ThemeModeProvider>);
    openMenu(0);
    clickMenuItem("Test Et");
    await vi.waitFor(() => {
      expect(screen.getByText("Test Sonucu")).toBeVisible();
    });
    expect(screen.getByText("950")).toBeVisible();
    expect(screen.getByText("95.00%")).toBeVisible();
    await act(async () => {
      fireEvent.click(screen.getByText("Kapat"));
    });
    await vi.waitFor(() => {
      expect(screen.queryByText("Test Sonucu")).not.toBeInTheDocument();
    });
  });

  it("aktivasyon dialogunu açar ve onaylar", async () => {
    const onActivate = vi.fn().mockResolvedValue(undefined);
    const items: RuleListItem[] = [{
      id: "rule-1", code: "TEST", name: "Test Kuralı", datasetId: "ds-1",
      dimension: "COMPLETENESS", status: "DRAFT", versionId: "rv-1", versionNo: 1,
      ruleType: "REQUIRED", criticality: "MEDIUM", createdAt: "2026-07-24T10:00:00Z",
      availableActions: ["ACTIVATE"], version: 1,
    }];
    render(<ThemeModeProvider><MemoryRouter><RulesPage items={items} onActivateRule={onActivate} /></MemoryRouter></ThemeModeProvider>);
    openMenu(0);
    clickMenuItem("Aktifleştir");
    expect(screen.getByText("Kuralı Aktifleştir")).toBeVisible();
    // Dialog içindeki "Aktifleştir" butonuna tıkla (menu item'dan ayırmak için getAllByText kullan)
    await act(async () => {
      fireEvent.click(screen.getAllByText("Aktifleştir").pop()!);
    });
    await vi.waitFor(() => expect(onActivate).toHaveBeenCalledWith(items[0]));
  });

  it("onay isteği dialogunu açar", async () => {
    const onRequest = vi.fn().mockResolvedValue(undefined);
    const items: RuleListItem[] = [{
      id: "rule-1", code: "TEST", name: "Test Kuralı", datasetId: "ds-1",
      dimension: "COMPLETENESS", status: "DRAFT", versionId: "rv-1", versionNo: 1,
      ruleType: "REQUIRED", criticality: "CRITICAL", createdAt: "2026-07-24T10:00:00Z",
      availableActions: ["REQUEST_APPROVAL"], version: 1,
    }];
    render(<ThemeModeProvider><MemoryRouter><RulesPage items={items} onRequestApproval={onRequest} /></MemoryRouter></ThemeModeProvider>);
    openMenu(0);
    clickMenuItem("Onaya Gönder");
    expect(screen.getByText("Onay İsteği Gönder")).toBeVisible();
    await act(async () => {
      fireEvent.click(screen.getAllByText("Onaya Gönder").pop()!);
    });
    await vi.waitFor(() => expect(onRequest).toHaveBeenCalledWith(items[0]));
  });

  it("onay kararı dialogunu açar ve karar gönderir", async () => {
    const onDecide = vi.fn().mockResolvedValue(undefined);
    const items: RuleListItem[] = [{
      id: "rule-1", code: "TEST", name: "Test Kuralı", datasetId: "ds-1",
      dimension: "COMPLETENESS", status: "DRAFT", versionId: "rv-1", versionNo: 1,
      ruleType: "REQUIRED", criticality: "CRITICAL", createdAt: "2026-07-24T10:00:00Z",
      availableActions: ["DECIDE_APPROVAL"], version: 1,
      pendingApprovalRequestId: "apr-test-1",
    }];
    render(<ThemeModeProvider><MemoryRouter><RulesPage items={items} onDecideApproval={onDecide} /></MemoryRouter></ThemeModeProvider>);
    openMenu(0);
    clickMenuItem("Onayla/Reddet");
    expect(screen.getByText("Onay Kararı — Test Kuralı")).toBeVisible();
    // Dialog içindeki input'u label ile bul
    const dialog = screen.getByRole("dialog");
    // Labelları kontrol et - dialog içinde sadece bir tane "Gerekçe Kodu" label'i olmalı
    const inputs = dialog.querySelectorAll("input[type='text']");
    expect(inputs.length).toBeGreaterThanOrEqual(1);
    fireEvent.change(inputs[0], { target: { value: "RULE_OK" } });
    await act(async () => {
      fireEvent.click(screen.getByText("Kararı Kaydet"));
    });
    await vi.waitFor(() => expect(onDecide).toHaveBeenCalledWith(items[0], "apr-test-1", "APPROVE", "RULE_OK"));
  });

  it("onay geri çekme dialogunu açar", async () => {
    const onWithdraw = vi.fn().mockResolvedValue(undefined);
    const items: RuleListItem[] = [{
      id: "rule-1", code: "TEST", name: "Test Kuralı", datasetId: "ds-1",
      dimension: "COMPLETENESS", status: "DRAFT", versionId: "rv-1", versionNo: 1,
      ruleType: "REQUIRED", criticality: "CRITICAL", createdAt: "2026-07-24T10:00:00Z",
      availableActions: ["WITHDRAW_APPROVAL"], version: 1,
      pendingApprovalRequestId: "apr-test-2",
    }];
    render(<ThemeModeProvider><MemoryRouter><RulesPage items={items} onWithdrawApproval={onWithdraw} /></MemoryRouter></ThemeModeProvider>);
    openMenu(0);
    clickMenuItem("Onayı Geri Çek");
    expect(screen.getByText("Onayı Geri Çek — Test Kuralı")).toBeVisible();
    // Gerekçe Kodu input'u dialog içinde
    const dialog = screen.getByRole("dialog");
    const inputs = dialog.querySelectorAll("input");
    const reasonInput = Array.from(inputs).find((el) => el.getAttribute("type") !== "number");
    if (reasonInput) {
      fireEvent.change(reasonInput, { target: { value: "CHANGED" } });
    }
    await act(async () => {
      fireEvent.click(screen.getByText("Geri Çek"));
    });
    await vi.waitFor(() => expect(onWithdraw).toHaveBeenCalledWith(items[0], "apr-test-2", "CHANGED"));
  });

  it("pasifleştirme dialogunu açar ve onaylar", async () => {
    const onPassivate = vi.fn().mockResolvedValue(undefined);
    const items: RuleListItem[] = [{
      id: "rule-1", code: "TEST", name: "Test Kuralı", datasetId: "ds-1",
      dimension: "COMPLETENESS", status: "ACTIVE", versionId: "rv-1", versionNo: 1,
      ruleType: "REQUIRED", criticality: "MEDIUM", createdAt: "2026-07-24T10:00:00Z",
      availableActions: ["CREATE_VERSION", "PASSIVATE"], version: 1,
    }];
    render(<ThemeModeProvider><MemoryRouter><RulesPage items={items} onPassivateRule={onPassivate} /></MemoryRouter></ThemeModeProvider>);
    openMenu(0);
    clickMenuItem("Pasifleştir");
    expect(screen.getByText("Kuralı Pasifleştir")).toBeVisible();
    expect(screen.getByText(/Bu işlem geri alınamaz/)).toBeVisible();
    await act(async () => {
      fireEvent.click(screen.getAllByText("Pasifleştir").pop()!);
    });
    await vi.waitFor(() => expect(onPassivate).toHaveBeenCalledWith(items[0]));
  });

  it("pasifleştirme dialogunda vazgeç butonu iptal eder", async () => {
    const onPassivate = vi.fn();
    const items: RuleListItem[] = [{
      id: "rule-1", code: "TEST", name: "Test Kuralı", datasetId: "ds-1",
      dimension: "COMPLETENESS", status: "ACTIVE", versionId: "rv-1", versionNo: 1,
      ruleType: "REQUIRED", criticality: "MEDIUM", createdAt: "2026-07-24T10:00:00Z",
      availableActions: ["PASSIVATE"], version: 1,
    }];
    render(<ThemeModeProvider><MemoryRouter><RulesPage items={items} onPassivateRule={onPassivate} /></MemoryRouter></ThemeModeProvider>);
    openMenu(0);
    clickMenuItem("Pasifleştir");
    expect(screen.getByText("Kuralı Pasifleştir")).toBeVisible();
    await act(async () => {
      fireEvent.click(screen.getByText("Vazgeç"));
    });
    await vi.waitFor(() => {
      expect(screen.queryByText("Kuralı Pasifleştir")).not.toBeInTheDocument();
    });
    expect(onPassivate).not.toHaveBeenCalled();
  });

  it("hata durumunda eylem hatasını gösterir", async () => {
    const onPassivate = vi.fn().mockRejectedValue(new Error("fail"));
    const items: RuleListItem[] = [{
      id: "rule-1", code: "TEST", name: "Test Kuralı", datasetId: "ds-1",
      dimension: "COMPLETENESS", status: "ACTIVE", versionId: "rv-1", versionNo: 1,
      ruleType: "REQUIRED", criticality: "MEDIUM", createdAt: "2026-07-24T10:00:00Z",
      availableActions: ["PASSIVATE"], version: 1,
    }];
    render(<ThemeModeProvider><MemoryRouter><RulesPage items={items} onPassivateRule={onPassivate} /></MemoryRouter></ThemeModeProvider>);
    openMenu(0);
    clickMenuItem("Pasifleştir");
    await act(async () => {
      fireEvent.click(screen.getAllByText("Pasifleştir").pop()!);
    });
    await vi.waitFor(() => {
      const errors = screen.getAllByText("Kural pasifleştirilemedi.");
      expect(errors.length).toBeGreaterThanOrEqual(1);
    });
  });
});