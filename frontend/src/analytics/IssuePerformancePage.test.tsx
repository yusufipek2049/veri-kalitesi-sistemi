import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { AnalyticsApiError } from "./api";
import type { AnalyticsEnvelope } from "./api";
import { IssuePerformancePage } from "./IssuePerformancePage";

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return { ...actual, fetchIssuePerformance: vi.fn() };
});

const { fetchIssuePerformance } = await import("./api");
const fetchMock = vi.mocked(fetchIssuePerformance);

function envelope(overrides: Partial<AnalyticsEnvelope> = {}): AnalyticsEnvelope {
  return {
    api_version: "v1",
    data_origin: "postgresql-runtime",
    correlation_id: "correlation-1",
    as_of: "2026-08-16T10:00:00Z",
    applied_filters: {},
    summary: {},
    breakdowns: {},
    items: [],
    ...overrides,
  };
}

function renderPage() {
  return render(
    <ThemeModeProvider>
      <MemoryRouter initialEntries={["/analytics/issues"]}>
        <IssuePerformancePage />
      </MemoryRouter>
    </ThemeModeProvider>,
  );
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("Issue performans ekranı", () => {
  it("açık issue varken satır listesi boş olsa da boş durum göstermez", async () => {
    // F-06: durum, bir önceki render'in summary state'inden değil bu yanıttan
    // hesaplanmalı; aksi halde açık issue varken ekran yanlışlıkla boşalırdı.
    fetchMock.mockResolvedValue(
      envelope({ summary: { open_issue_count: 7, critical_open_count: 2 }, items: [] }),
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Açık Issue")).toBeVisible();
    });
    expect(screen.queryByText("Gösterilecek issue verisi bulunamadı.")).not.toBeInTheDocument();
    expect(screen.getByText("7")).toBeVisible();
  });

  it("hem satır hem açık issue yokken boş durumu gösterir", async () => {
    fetchMock.mockResolvedValue(envelope({ summary: { open_issue_count: 0 }, items: [] }));

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Gösterilecek issue verisi bulunamadı.")).toBeVisible();
    });
  });

  it("açık issue yokken bile satır varsa veriyi gösterir", async () => {
    fetchMock.mockResolvedValue(
      envelope({
        summary: { open_issue_count: 0 },
        items: [{ issue_id: "issue-1", status: "RESOLVED" }],
      }),
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Açık Issue")).toBeVisible();
    });
    expect(screen.queryByText("Gösterilecek issue verisi bulunamadı.")).not.toBeInTheDocument();
  });

  it("yetkisiz yanıtta korelasyon kimliğiyle yetki uyarısı gösterir", async () => {
    fetchMock.mockRejectedValue(
      new AnalyticsApiError("forbidden", "correlation-forbidden"),
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Bu analitik görünümü için yetkiniz bulunmuyor.")).toBeVisible();
    });
    expect(screen.getByText("Correlation: correlation-forbidden")).toBeVisible();
  });

  it("teknik hatada hata durumunu gösterir", async () => {
    fetchMock.mockRejectedValue(new Error("network down"));

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Issue performans verisi yüklenemedi.")).toBeVisible();
    });
  });
});
