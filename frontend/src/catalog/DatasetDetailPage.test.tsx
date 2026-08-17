import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { CatalogApiError } from "./api";
import { DatasetDetailPage } from "./DatasetDetailPage";
import type { CatalogDataset, DatasetPreview, MetadataDiff } from "./model";

vi.mock("../components/NotificationBell", () => ({
  NotificationBell: () => <button aria-label="Bildirimler">Bildirimler</button>,
}));

function dataset(overrides: Partial<CatalogDataset> = {}): CatalogDataset {
  return {
    id: "ds-1",
    dataSourceId: "source-1",
    namespace: "public",
    name: "accounts",
    datasetType: "TABLE",
    status: "ACTIVE",
    criticality: "MEDIUM",
    estimatedRowCount: 1000,
    fieldCount: 5,
    version: 1,
    ownerId: null,
    timelinessNature: null,
    ...overrides,
  };
}

function renderPage(nature: CatalogDataset["timelinessNature"]) {
  return render(
    <ThemeModeProvider>
      <MemoryRouter>
        <DatasetDetailPage dataset={dataset({ timelinessNature: nature })} />
      </MemoryRouter>
    </ThemeModeProvider>,
  );
}

describe("DatasetDetailPage zamanlılık niteliği", () => {
  it("atanmış niteliği rozet olarak gösterir", () => {
    renderPage("BATCH_TIME");
    expect(screen.getByText("Zamanlılık niteliği")).toBeVisible();
    expect(screen.getByText("Toplu (Batch)")).toBeVisible();
  });

  it("atanmamış nitelikte job uyarısı gösterir", () => {
    renderPage(null);
    expect(screen.getByText("Atanmadı (job için gerekli)")).toBeVisible();
  });
});

function previewFixture(): DatasetPreview {
  return {
    tableName: "accounts",
    namespace: "public",
    limit: 50,
    columns: [
      { name: "id", nativeDataType: "integer", isSensitive: false },
      { name: "ad_soyad", nativeDataType: "text", isSensitive: true },
    ],
    rows: [
      ["1", "•••"],
      ["2", null],
    ],
  };
}

describe("DatasetDetailPage veri önizleme", () => {
  it("satırları yükler ve hassas kolonu rozetle işaretler", async () => {
    const onPreviewRows = vi.fn().mockResolvedValue(previewFixture());
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <DatasetDetailPage dataset={dataset()} onPreviewRows={onPreviewRows} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    expect(screen.getByText("Veri Önizleme")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /Satırları görüntüle/ }));

    expect(await screen.findByRole("table", { name: "Tablo satır önizlemesi" })).toBeVisible();
    expect(onPreviewRows).toHaveBeenCalledTimes(1);
    expect(screen.getByText("public.accounts")).toBeVisible();
    expect(screen.getByText("2 satır (ilk 50 ile sınırlı)")).toBeVisible();
    expect(screen.getByText("Hassas alanlar maskelendi")).toBeVisible();
    expect(screen.getByText("Hassas")).toBeVisible();
    expect(screen.getByText("•••")).toBeVisible();
    expect(screen.getByText("NULL")).toBeVisible();
  });

  it("desteklenmeyen kaynak tipinde Türkçe uyarı gösterir", async () => {
    const onPreviewRows = vi
      .fn()
      .mockRejectedValue(new CatalogApiError(409, "PREVIEW_UNSUPPORTED_SOURCE_TYPE", "corr-1"));
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <DatasetDetailPage dataset={dataset()} onPreviewRows={onPreviewRows} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /Satırları görüntüle/ }));

    expect(
      await screen.findByText(
        "Satır önizleme yalnızca PostgreSQL veri kaynakları için desteklenir.",
      ),
    ).toBeVisible();
  });

  it("onPreviewRows yoksa önizleme bölümünü gizler", () => {
    renderPage(null);
    expect(screen.queryByText("Veri Önizleme")).not.toBeInTheDocument();
  });
});

function pendingDiff(): MetadataDiff {
  return {
    metadataDiffId: "diff-1",
    discoveryId: 1,
    dataSourceId: "source-1",
    status: "PENDING",
    addedObjects: [
      {
        object_type: "DATA_FIELD",
        namespace: "public",
        dataset_name: "accounts",
        field_name: "email",
        new_values: { native_data_type: "text" },
      },
    ],
    changedObjects: [
      {
        object_type: "DATA_FIELD",
        namespace: "public",
        dataset_name: "accounts",
        field_name: "amount",
        new_values: { native_data_type: "numeric" },
      },
    ],
    removedObjects: [
      {
        object_type: "DATA_FIELD",
        namespace: "public",
        dataset_name: "accounts",
        field_name: "legacy",
      },
    ],
    requiresRuleReview: false,
  };
}

describe("DatasetDetailPage bekleyen fark paneli", () => {
  it("varsayılan seçim boşken gönderimi kapalı tutar ve doğrudan uygulama butonu yoktur", () => {
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <DatasetDetailPage dataset={dataset()} latestDiff={pendingDiff()} onSubmitDiffApproval={vi.fn()} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    expect(screen.getByText("Bekleyen Fark")).toBeVisible();
    expect(screen.getByRole("button", { name: "Onaya gönder" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Farkı uygula" })).not.toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "public.accounts.email" })).not.toBeChecked();
  });

  it("seçili objeleri anahtar sözleşmesiyle gönderir ve onay beklenen duruma geçer", async () => {
    const onSubmitDiffApproval = vi.fn().mockResolvedValue(undefined);
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <DatasetDetailPage
            dataset={dataset()}
            latestDiff={pendingDiff()}
            onSubmitDiffApproval={onSubmitDiffApproval}
          />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    fireEvent.click(screen.getByRole("checkbox", { name: "public.accounts.email" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "public.accounts.amount" }));
    fireEvent.click(screen.getByRole("button", { name: "Onaya gönder" }));

    await waitFor(() =>
      expect(onSubmitDiffApproval).toHaveBeenCalledWith("diff-1", [
        ["ADDED", "DATA_FIELD", "public", "accounts", "email"],
        ["CHANGED", "DATA_FIELD", "public", "accounts", "amount"],
      ]),
    );
    expect(await screen.findByText(/Onay bekleniyor/)).toBeVisible();
    expect(screen.getByRole("checkbox", { name: "public.accounts.legacy" })).toBeDisabled();
  });

  it("gönderim başarısızsa hata mesajı gösterir", async () => {
    const onSubmitDiffApproval = vi.fn().mockRejectedValue(new Error("conflict"));
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <DatasetDetailPage
            dataset={dataset()}
            latestDiff={pendingDiff()}
            onSubmitDiffApproval={onSubmitDiffApproval}
          />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    fireEvent.click(screen.getByRole("checkbox", { name: "public.accounts.email" }));
    fireEvent.click(screen.getByRole("button", { name: "Onaya gönder" }));

    expect(await screen.findByText("Onay talebi gönderilemedi.")).toBeVisible();
    expect(screen.queryByText(/Onay bekleniyor/)).not.toBeInTheDocument();
  });
});

describe("DatasetDetailPage nitelik değiştirme", () => {
  it("Nitelik Değiştir butonu ve diyaloğu açılır", () => {
    const onSubmitAttributeChange = vi.fn().mockResolvedValue(undefined);
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <DatasetDetailPage
            dataset={dataset({ criticality: "MEDIUM", status: "ACTIVE" })}
            onSubmitAttributeChange={onSubmitAttributeChange}
          />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    expect(screen.getByRole("button", { name: /Nitelik Değiştir/ })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /Nitelik Değiştir/ }));
    expect(screen.getByText("Kritik Nitelik Değişikliği")).toBeVisible();
    expect(screen.getByText("Mevcut değer:")).toBeVisible();
    expect(screen.getByRole("button", { name: "Talep Gönder" })).toBeVisible();
  });

  it("onSubmitAttributeChange yoksa butonu gizler", () => {
    renderPage(null);
    expect(screen.queryByRole("button", { name: /Nitelik Değiştir/ })).not.toBeInTheDocument();
  });

  it("talep gönderiminde doğru parametreleri iletir", async () => {
    const onSubmitAttributeChange = vi.fn().mockResolvedValue(undefined);
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <DatasetDetailPage
            dataset={dataset({ criticality: "MEDIUM" })}
            onSubmitAttributeChange={onSubmitAttributeChange}
          />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /Nitelik Değiştir/ }));
    fireEvent.click(screen.getByRole("button", { name: "Talep Gönder" }));

    await waitFor(() =>
      expect(onSubmitAttributeChange).toHaveBeenCalledWith(
        "criticality",
        "CRITICAL",
        "METADATA.CRITICALITY.CHANGE",
      ),
    );
    expect(await screen.findByText(/Değişiklik talebi gönderildi/)).toBeVisible();
  });

  it("gönderim başarısızsa hata gösterir", async () => {
    const onSubmitAttributeChange = vi.fn().mockRejectedValue(new Error("fail"));
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <DatasetDetailPage
            dataset={dataset()}
            onSubmitAttributeChange={onSubmitAttributeChange}
          />
        </MemoryRouter>
      </ThemeModeProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /Nitelik Değiştir/ }));
    fireEvent.click(screen.getByRole("button", { name: "Talep Gönder" }));

    expect(await screen.findByText("Nitelik değişiklik talebi gönderilemedi.")).toBeVisible();
  });
});
