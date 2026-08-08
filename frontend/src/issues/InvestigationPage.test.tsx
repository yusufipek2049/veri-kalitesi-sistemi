import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { InvestigationPage } from "./InvestigationPage";
import type { EvidenceComponent, GovernanceProjection, InvestigationEvidence, LineageSnapshot } from "./model";

function renderPage(props: Partial<React.ComponentProps<typeof InvestigationPage>> & { assetRef: string }) {
  return render(
    <ThemeModeProvider>
      <MemoryRouter>
        <InvestigationPage {...props} />
      </MemoryRouter>
    </ThemeModeProvider>,
  );
}

const mockProjection: GovernanceProjection = {
  assetRef: "source-customer",
  governanceProfileStatus: "ACTIVE",
  governanceReasonCodes: [],
  governanceVersion: "GP_V1:source-customer:1",
  governanceAssetRef: "source-customer",
  criticalAssetStatus: "Observed",
  riskStatus: "Calculated",
  slaStatus: "Unknown",
};

const mockSnapshot: LineageSnapshot = {
  snapshotId: "snap-1",
  snapshotKind: "LINEAGE_EVENTS",
  subjectRef: "source-customer",
  versionLabel: "v1",
  digest: "sha256:abc123",
  createdAt: "2026-08-01T10:00:00Z",
  payload: { events: [] },
};

function mockComponent(overrides?: Partial<EvidenceComponent>): EvidenceComponent {
  return {
    source: "Observed",
    value: "test-value",
    references: [],
    ...overrides,
  };
}

const mockEvidence: InvestigationEvidence = {
  issueId: "issue-1",
  ruleDescription: mockComponent({ source: "Observed", value: "Müşteri TC kimlik no 11 haneli olmalıdır", references: ["rule-v3"] }),
  expectedSummary: mockComponent({ source: "Observed", value: '{"null_count": 0, "min_length": 11}', references: ["query-ref-1"] }),
  actualSummary: mockComponent({ source: "Observed", value: '{"null_count": 42, "min_length": 9}', references: ["query-ref-1"] }),
  maskedSamples: mockComponent({ source: "Observed", value: ["123456****1", "987654****2", "111111****3"], references: ["fp-001"] }),
  similarHistory: mockComponent({ source: "Unknown", value: null, references: [] }),
  recommendation: mockComponent({ source: "Unknown", value: null, references: [] }),
  ruleVersionId: "rule-v3",
  irVersion: "ir-v1",
  evidenceFingerprint: "fp-001",
  evidenceQueryReference: "query-ref-1",
  evidencePlanReference: "plan-ref-1",
  authorizationPolicyVersion: "AUTH_POL_V2",
};

describe("InvestigationPage", () => {
  it("başarılı veride yönetişim projeksiyonu ve lineage kanıtını gösterir", () => {
    renderPage({
      assetRef: "source-customer",
      snapshotId: "snap-1",
      state: "ready",
      data: { snapshot: mockSnapshot, projection: mockProjection, evidence: null },
      correlationId: "corr-1",
    });
    expect(screen.getByText("Yönetişim Projeksiyonu")).toBeTruthy();
    expect(screen.getByText("Gözlemlenen")).toBeTruthy();
    expect(screen.getByText("Hesaplanan")).toBeTruthy();
    expect(screen.getByText("Bilinmeyen")).toBeTruthy();
    expect(screen.getByText("Lineage Kanıtı")).toBeTruthy();
    expect(screen.getByText("LINEAGE_EVENTS")).toBeTruthy();
  });

  it("kanıt yoksa Unknown olarak gösterir ve kısmi veri sunmaz", () => {
    renderPage({
      assetRef: "source-unknown",
      state: "ready",
      data: {
        snapshot: null,
        projection: {
          ...mockProjection,
          governanceProfileStatus: "NO_ACTIVE_PROFILE",
          criticalAssetStatus: "Unknown",
          riskStatus: "Unknown",
          slaStatus: "Unknown",
          governanceVersion: null,
          governanceAssetRef: null,
        },
        evidence: null,
      },
    });
    const unknownLabels = screen.getAllByText("Bilinmeyen");
    expect(unknownLabels.length).toBeGreaterThanOrEqual(3);
  });

  it("503 durumunda fail-closed bilgilendirme gösterir", () => {
    renderPage({
      assetRef: "source-customer",
      state: "unavailable",
      correlationId: "corr-503",
    });
    expect(screen.getByText("Kanıt hizmeti kullanılamıyor")).toBeTruthy();
    expect(screen.getByText(/Kısmi veri kanıt olarak sunulmaz/)).toBeTruthy();
    expect(screen.getAllByText(/corr-503/).length).toBeGreaterThanOrEqual(1);
  });

  it("403/404 durumunda veri sızdırmadan gösterir", () => {
    renderPage({
      assetRef: "source-restricted",
      state: "unauthorized",
      correlationId: "corr-403",
    });
    expect(screen.getByText("Erişim reddedildi")).toBeTruthy();
    expect(screen.queryByText("source-restricted")).toBeNull();
  });

  it("404 durumunda kanıt bulunamadı gösterir", () => {
    renderPage({
      assetRef: "source-missing",
      state: "not-found",
      correlationId: "corr-404",
    });
    expect(screen.getByText("Kanıt bulunamadı")).toBeTruthy();
  });

  it("hipotez snapshot'larında Hipotez etiketi gösterir", () => {
    renderPage({
      assetRef: "source-customer",
      snapshotId: "snap-hyp",
      state: "ready",
      data: {
        snapshot: { ...mockSnapshot, snapshotKind: "ROOT_CAUSE_HYPOTHESIS" },
        projection: mockProjection,
        evidence: null,
      },
    });
    expect(screen.getByText("Hipotez")).toBeTruthy();
  });

  it("tam kanıtla tüm bileşenleri tek inceleme yüzeyinde gösterir (AC-01, AC-02)", () => {
    renderPage({
      assetRef: "source-customer",
      state: "ready",
      data: {
        snapshot: mockSnapshot,
        projection: mockProjection,
        evidence: mockEvidence,
      },
    });
    expect(screen.getByText("İnceleme Kanıtı")).toBeTruthy();
    expect(screen.getByText("Kural / sorgu açıklaması")).toBeTruthy();
    expect(screen.getByText(/Müşteri TC kimlik no 11 haneli olmalıdır/)).toBeTruthy();
    expect(screen.getByText("Beklenen değer")).toBeTruthy();
    expect(screen.getByText("Gerçekleşen değer")).toBeTruthy();
    expect(screen.getByText(/Maskeli kötü örnek/)).toBeTruthy();
    expect(screen.getByText("Yönetişim Projeksiyonu")).toBeTruthy();
    expect(screen.getByText("Lineage Kanıtı")).toBeTruthy();
  });

  it("her bileşenin kaynak sınıflandırmasını gösterir (AC-03)", () => {
    renderPage({
      assetRef: "source-customer",
      state: "ready",
      data: {
        snapshot: null,
        projection: mockProjection,
        evidence: mockEvidence,
      },
    });
    const observedLabels = screen.getAllByText("Gözlemlenen");
    expect(observedLabels.length).toBeGreaterThanOrEqual(3);
    const unknownLabels = screen.getAllByText("Bilinmeyen");
    expect(unknownLabels.length).toBeGreaterThanOrEqual(2);
  });

  it("Unknown bileşenleri gerekçeyle gösterir, boş/sıfır olarak değil (AC-04)", () => {
    renderPage({
      assetRef: "source-customer",
      state: "ready",
      data: {
        snapshot: null,
        projection: mockProjection,
        evidence: mockEvidence,
      },
    });
    expect(screen.getAllByText(/Bu bileşen için kanıt mevcut değildir/).length).toBeGreaterThanOrEqual(2);
  });

  it("maskeli kötü örnekleri maskeli olarak gösterir ve etiketler (AC-05)", () => {
    renderPage({
      assetRef: "source-customer",
      state: "ready",
      data: {
        snapshot: null,
        projection: mockProjection,
        evidence: mockEvidence,
      },
    });
    expect(screen.getByText("Maskeli")).toBeTruthy();
    expect(screen.getByText("123456****1")).toBeTruthy();
    expect(screen.getByText("987654****2")).toBeTruthy();
  });

  it("403/404 durumunda veri sızdırmadan bildirir (AC-06)", () => {
    renderPage({
      assetRef: "source-restricted",
      state: "unauthorized",
      correlationId: "corr-403-evidence",
    });
    expect(screen.getByText("Erişim reddedildi")).toBeTruthy();
    expect(screen.queryByText("source-restricted")).toBeNull();
    expect(screen.queryByText("İnceleme Kanıtı")).toBeNull();
  });

  it("kanıt referanslarını, kural sürümü ve politika sürümünü gösterir (AC-07)", () => {
    renderPage({
      assetRef: "source-customer",
      state: "ready",
      data: {
        snapshot: null,
        projection: mockProjection,
        evidence: mockEvidence,
      },
    });
    expect(screen.getByText("Kanıt referansları")).toBeTruthy();
    expect(screen.getByText("Kural sürümü: rule-v3")).toBeTruthy();
    expect(screen.getByText("IR sürümü: ir-v1")).toBeTruthy();
    expect(screen.getByText("Politika sürümü: AUTH_POL_V2")).toBeTruthy();
    expect(screen.getByText("Parmak izi: fp-001")).toBeTruthy();
    expect(screen.getByText("Sorgu: query-ref-1")).toBeTruthy();
    expect(screen.getByText("Plan: plan-ref-1")).toBeTruthy();
  });

  it("öneriyi hipotez olarak etiketler (AC-03)", () => {
    renderPage({
      assetRef: "source-customer",
      state: "ready",
      data: {
        snapshot: null,
        projection: mockProjection,
        evidence: mockEvidence,
      },
    });
    const hypothesisChips = screen.getAllByText("Hipotez");
    expect(hypothesisChips.length).toBeGreaterThanOrEqual(1);
  });

  it("bounded liste sınırlı olduğunu belirterek gösterir (AC-08)", () => {
    const manySamples = Array.from({ length: 15 }, (_, i) => `masked-${String(i).padStart(4, "0")}`);
    renderPage({
      assetRef: "source-customer",
      state: "ready",
      data: {
        snapshot: null,
        projection: mockProjection,
        evidence: {
          ...mockEvidence,
          maskedSamples: { source: "Observed", value: manySamples, references: ["fp-001"] },
        },
      },
    });
    expect(screen.getByText(/Liste sınırlı gösteriliyor/)).toBeTruthy();
  });
});
