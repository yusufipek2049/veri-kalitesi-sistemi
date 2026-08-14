import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { IssuesPage } from "./IssuesPage";
import type { IssueCreateInput } from "./model";

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

    fireEvent.click(screen.getByRole("button", { name: "DQI-2026-0017 işlemleri" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "İncelemeye al" }));

    expect(onStartInvestigation).toHaveBeenCalledWith(
      expect.objectContaining({ id: "issue-technical-risk", version: 1 }),
    );
    expect(await screen.findByText("DQI-2026-0017 incelemeye alındı.")).toBeVisible();
  });

  it("yetkili sorunu açık kaydetme işlemiyle yeniden atar", async () => {
    const onLoadAssignmentOptions = vi.fn().mockResolvedValue([
      {
        userId: "4ec96cb4-d150-45d2-9565-c1879d135f08",
        displayName: "Veri Sorumlusu A",
      },
    ]);
    const onReassign = vi.fn().mockResolvedValue(undefined);
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <IssuesPage
            onLoadAssignmentOptions={onLoadAssignmentOptions}
            onReassign={onReassign}
          />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "DQI-2026-0017 işlemleri" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Yeniden ata" }));
    await waitFor(() => expect(onLoadAssignmentOptions).toHaveBeenCalled());
    fireEvent.mouseDown(await screen.findByLabelText("Yeni sorumlu"));
    fireEvent.click(screen.getByRole("option", { name: "Veri Sorumlusu A" }));
    fireEvent.click(screen.getByRole("button", { name: "Kaydet" }));

    await waitFor(() => expect(onReassign).toHaveBeenCalledWith(
      expect.objectContaining({ id: "issue-technical-risk", version: 1 }),
      "4ec96cb4-d150-45d2-9565-c1879d135f08",
      "HIGH",
    ));
    expect(await screen.findByText("DQI-2026-0017 yeniden atandı.")).toBeVisible();
  });

  it("kaydedilmemiş atama değişikliğinde çıkış uyarısı gösterir", async () => {
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <IssuesPage
            onLoadAssignmentOptions={vi.fn().mockResolvedValue([{
              userId: "4ec96cb4-d150-45d2-9565-c1879d135f08",
              displayName: "Veri Sorumlusu A",
            }])}
          />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "DQI-2026-0017 işlemleri" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Yeniden ata" }));
    fireEvent.mouseDown(await screen.findByLabelText("Yeni sorumlu"));
    fireEvent.click(screen.getByRole("option", { name: "Veri Sorumlusu A" }));
    fireEvent.click(screen.getByRole("button", { name: "Vazgeç" }));

    expect(screen.getByText("Değişiklikler kaydedilmedi")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Forma dön" }));
    expect(await screen.findByRole("combobox", { name: "Yeni sorumlu" })).toBeVisible();
  });

  it("zorunlu kanıtla korumalı çözüm kaydını açıkça kaydeder", async () => {
    const onResolve = vi.fn().mockResolvedValue(undefined);
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <IssuesPage onResolve={onResolve} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "DQI-2026-0016 işlemleri" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Çözüm kaydet" }));
    fireEvent.change(screen.getByRole("textbox", { name: /Kök neden/ }), {
      target: { value: "Kaynak eşlemesi hatalı" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: /Düzeltici faaliyet/ }), {
      target: { value: "Eşleme yapılandırması düzeltildi" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: /Kanıt referansı/ }), {
      target: { value: "550e8400-e29b-41d4-a716-446655440000" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Kaydet" }));

    await waitFor(() => expect(onResolve).toHaveBeenCalledWith(
      expect.objectContaining({ id: "issue-account-investigation", version: 2 }),
      "Kaynak eşlemesi hatalı",
      "Eşleme yapılandırması düzeltildi",
      "550e8400-e29b-41d4-a716-446655440000",
      expect.stringMatching(/Z$/),
    ));
    expect(await screen.findByText("DQI-2026-0016 çözüm kaydı oluşturuldu.")).toBeVisible();
  });

  it("geçersiz kanıtı reddeder ve kaydedilmemiş çözümü korur", () => {
    const onResolve = vi.fn().mockResolvedValue(undefined);
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <IssuesPage onResolve={onResolve} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "DQI-2026-0016 işlemleri" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Çözüm kaydet" }));
    fireEvent.change(screen.getByRole("textbox", { name: /Kök neden/ }), {
      target: { value: "Kaynak eşlemesi hatalı" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: /Düzeltici faaliyet/ }), {
      target: { value: "Eşleme yapılandırması düzeltildi" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: /Kanıt referansı/ }), {
      target: { value: "ham-kayıt-değeri" },
    });

    expect(screen.getByText("Geçerli bir UUID girin.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Kaydet" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Vazgeç" }));
    expect(screen.getByText("Değişiklikler kaydedilmedi")).toBeVisible();
    expect(onResolve).not.toHaveBeenCalled();
  });

  it("CREATE_ISSUE eylemi varsa Yeni Sorun butonu gösterir", () => {
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <IssuesPage pageActions={["CREATE_ISSUE"]} onCreateIssue={vi.fn()} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    expect(screen.getByRole("button", { name: /Yeni Sorun/ })).toBeVisible();
  });

  it("CREATE_ISSUE eylemi yoksa Yeni Sorun butonu göstermez", () => {
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <IssuesPage pageActions={[]} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    expect(screen.queryByRole("button", { name: /Yeni Sorun/ })).not.toBeInTheDocument();
  });

  it("oluşturma dialog'u açar, doldurur ve onSuccess çağırır", async () => {
    const onCreateIssue = vi.fn().mockResolvedValue(undefined);
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <IssuesPage
            pageActions={["CREATE_ISSUE"]}
            onCreateIssue={onCreateIssue}
          />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /Yeni Sorun/ }));
    expect(screen.getByText("Yeni sorun oluştur")).toBeVisible();

    fireEvent.change(screen.getByRole("textbox", { name: /Başlık/ }), {
      target: { value: "Manuel kalite sorunu" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: /Kapsam kimliği/ }), {
      target: { value: "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Oluştur" }));

    await waitFor(() => expect(onCreateIssue).toHaveBeenCalledWith({
      title: "Manuel kalite sorunu",
      scopeType: "DATASET",
      scopeId: "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb",
      priority: "MEDIUM",
    } satisfies IssueCreateInput));
    expect(await screen.findByText("Yeni sorun oluşturuldu.")).toBeVisible();
  });

  it("oluşturma dialog'u boş başlılda submit çağrılmaz", () => {
    const onCreateIssue = vi.fn();
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <IssuesPage
            pageActions={["CREATE_ISSUE"]}
            onCreateIssue={onCreateIssue}
          />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /Yeni Sorun/ }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("Yeni sorun oluştur")).toBeVisible();
    // Submit button should be disabled when title and scope are empty
    expect(within(dialog).getByRole("button", { name: "Oluştur" })).toBeDisabled();
    expect(onCreateIssue).not.toHaveBeenCalled();
  });

  it("MANUAL trigger türünü Türkçe etiketle gösterir", () => {
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <IssuesPage
            items={[{
              id: "issue-manual-ds05",
              issueNo: "DQI-2026-0200",
              title: "Manuel sorun",
              sourceEventType: "MANUAL",
              triggerType: "MANUAL",
              scopeType: "DATASET",
              scopeId: "dataset-x",
              scopeDisplayName: "Dataset X",
              scopeParentName: null,
              status: "NEW",
              priority: "MEDIUM",
              occurrenceCount: 1,
              version: 1,
              sourceExecutionId: null,
              sourceRuleVersionId: null,
              availableActions: [],
              createdAt: "2026-08-05T10:00:00Z",
              updatedAt: "2026-08-05T10:00:00Z",
              lastSeenAt: "2026-08-05T10:00:00Z",
            }]}
          />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    expect(screen.getByText(/Manuel/)).toBeVisible();
  });
});
