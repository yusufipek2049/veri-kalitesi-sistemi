import type { StatusTone } from "../theme/tokens";

export type DashboardState =
  | "normal"
  | "loading"
  | "empty"
  | "error"
  | "unauthorized"
  | "long-content";

export interface KpiViewModel {
  id: string;
  label: string;
  value: string;
  detail: string;
  tone: StatusTone;
  statusLabel: string;
}

export interface TrendObservation {
  date: string;
  displayDate: string;
  rawScore: number | null;
  finalScore: number | null;
  qualification: string;
  usageDecision: string;
  coverageRate: number | null;
  technicalStatus: "Başarılı" | "Teknik Hata" | "Hesaplanmadı";
  official: boolean;
}

export interface AlertViewModel {
  id: string;
  title: string;
  scope: string;
  time: string;
  tone: StatusTone;
  statusLabel: string;
  nextAction: string;
}

export interface FieldScoreViewModel {
  id: string;
  label: string;
  score: number | null;
  tone: StatusTone;
  statusLabel: string;
}

export interface QualityDimensionCellViewModel {
  dimension: string;
  score: number | null;
  tone: StatusTone;
  statusLabel: string;
}

export interface QualityDimensionRowViewModel {
  fieldId: string;
  fieldLabel: string;
  cells: QualityDimensionCellViewModel[];
}

export interface DashboardViewModel {
  kpis: KpiViewModel[];
  trendObservations: TrendObservation[];
  alerts: AlertViewModel[];
  fieldScores: FieldScoreViewModel[];
  qualityDimensionRows: QualityDimensionRowViewModel[];
  dataNotice: string;
  trendDescription: string;
  measurementNote: string;
}

export interface DashboardApiObservation {
  quality_score_id: string;
  scope_type: "ENTERPRISE" | "SOURCE";
  scope_id: string | null;
  score_value: string | number | null;
  score_status: string;
  level: string | null;
  calculated_at: string;
}

export interface DashboardApiPeriod {
  period_start: string;
  period_end: string;
  observations: DashboardApiObservation[];
}

export interface DashboardOperationalIndicatorsApiResponse {
  measurement_qualification: {
    status: "NO_DATA" | "VALIDATION_REQUIRED" | "TECHNICAL_FAILURE";
    evaluated_scope_count: number;
    reason_codes: string[];
    policy_version: string | null;
  };
  critical_controls: {
    status: "NOT_AVAILABLE";
    reason_code: string;
    passed_count: number | null;
    failed_count: number | null;
    not_evaluated_count: number | null;
  };
  technical_errors: {
    observation_count: number;
    execution_count: number;
    affected_source_count: number;
    last_occurred_at: string | null;
  };
}

export interface DashboardSummaryApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  as_of: string;
  has_data: boolean;
  periods: DashboardApiPeriod[];
  operational_indicators: DashboardOperationalIndicatorsApiResponse;
}

export const kpis: KpiViewModel[] = [
  {
    id: "quality-score",
    label: "Nihai Kalite Skoru",
    value: "87,4",
    detail: "Ham skor 89,1 · Model v3",
    tone: "success",
    statusLabel: "Yeterli",
  },
  {
    id: "qualification",
    label: "Ölçüm Yeterliliği",
    value: "%94",
    detail: "47 / 50 kural değerlendirildi",
    tone: "warning",
    statusLabel: "Sınırlı Kapsam",
  },
  {
    id: "critical-rules",
    label: "Kritik Kontroller",
    value: "2",
    detail: "18 kritik kontrolden 2 ihlal",
    tone: "critical",
    statusLabel: "Kritik İhlal",
  },
  {
    id: "technical-errors",
    label: "Teknik Hatalar",
    value: "3",
    detail: "Son olay 14:20 · Kaliteye katılmadı",
    tone: "technical",
    statusLabel: "Teknik Hata",
  },
];

export const longContentKpis: KpiViewModel[] = kpis.map((item, index) =>
  index === 1
    ? {
        ...item,
        label: "Ölçüm Yeterliliği ve Kanıt Tamamlığı Değerlendirmesi",
        detail: "Zorunlu kritik kontrollerden üçünün teknik değerlendirmesi tamamlanmadığı için kapsam sınırlıdır",
      }
    : item,
);

export const trendObservations: TrendObservation[] = [
  { date: "2026-06-23", displayDate: "23 Haz", rawScore: 72.1, finalScore: 72.1, qualification: "Qualified", usageDecision: "Allowed", coverageRate: 98, technicalStatus: "Başarılı", official: true },
  { date: "2026-06-27", displayDate: "27 Haz", rawScore: 76.8, finalScore: 76.8, qualification: "Qualified", usageDecision: "Allowed", coverageRate: 97, technicalStatus: "Başarılı", official: true },
  { date: "2026-07-01", displayDate: "1 Tem", rawScore: 78.2, finalScore: 78.2, qualification: "Qualified", usageDecision: "Allowed", coverageRate: 97, technicalStatus: "Başarılı", official: true },
  { date: "2026-07-05", displayDate: "5 Tem", rawScore: null, finalScore: null, qualification: "TechnicalFailure", usageDecision: "Undetermined", coverageRate: null, technicalStatus: "Teknik Hata", official: false },
  { date: "2026-07-09", displayDate: "9 Tem", rawScore: 82.4, finalScore: 82.4, qualification: "Qualified", usageDecision: "Allowed", coverageRate: 96, technicalStatus: "Başarılı", official: true },
  { date: "2026-07-13", displayDate: "13 Tem", rawScore: 84.6, finalScore: 84.6, qualification: "ProvisionallyQualified", usageDecision: "ConditionallyAllowed", coverageRate: 92, technicalStatus: "Başarılı", official: false },
  { date: "2026-07-17", displayDate: "17 Tem", rawScore: 86.2, finalScore: 86.2, qualification: "Qualified", usageDecision: "Allowed", coverageRate: 96, technicalStatus: "Başarılı", official: true },
  { date: "2026-07-21", displayDate: "21 Tem", rawScore: 89.1, finalScore: 87.4, qualification: "LimitedCoverage", usageDecision: "ConditionallyAllowed", coverageRate: 94, technicalStatus: "Başarılı", official: true },
];

export const syntheticFieldScores: FieldScoreViewModel[] = [
  { id: "field-finance", label: "Finans", score: 94.2, tone: "success", statusLabel: "İyi" },
  { id: "field-customer", label: "Müşteri", score: 89, tone: "warning", statusLabel: "İzlenmeli" },
  { id: "field-operations", label: "Operasyon", score: 86.4, tone: "info", statusLabel: "Kabul Edilebilir" },
  { id: "field-risk", label: "Risk", score: 78.1, tone: "warning", statusLabel: "Riskli" },
  { id: "field-reference", label: "Referans", score: 68.7, tone: "critical", statusLabel: "Kritik" },
];

const qualityDimensions = ["Tamlık", "Doğruluk", "Geçerlilik", "Tutarlılık", "Tekillik", "Güncellik", "Bütünlük"];

const dimensionScores: Array<[string, Array<number | null>]> = [
  ["Finans", [96, 94, 93, 90, 98, 91, 95]],
  ["Müşteri", [69, 89, 94, 88, 96, 82, 86]],
  ["Operasyon", [87, 88, 84, 92, 89, null, 88]],
  ["Risk", [79, 80, 81, 70, 88, 77, 76]],
  ["Referans", [null, 66, 78, 64, 86, 68, 69]],
];

export const syntheticQualityDimensionRows: QualityDimensionRowViewModel[] = dimensionScores.map(
  ([fieldLabel, scores], rowIndex) => ({
    fieldId: `dimension-field-${rowIndex + 1}`,
    fieldLabel,
    cells: qualityDimensions.map((dimension, index) => dimensionCell(dimension, scores[index] ?? null)),
  }),
);

export const alerts: AlertViewModel[] = [
  {
    id: "ALT-SYN-1042",
    title: "Referans bütünlüğü kritik eşik altında",
    scope: "Sentetik Alan A · 3 kural etkileniyor",
    time: "8 dk",
    tone: "critical",
    statusLabel: "Kritik İhlal",
    nextAction: "İncele",
  },
  {
    id: "ALT-SYN-1041",
    title: "Kaynak bağlantısı zaman aşımına uğradı",
    scope: "Sentetik Kaynak B · İzleme kodu SYN-7F21",
    time: "21 dk",
    tone: "technical",
    statusLabel: "Teknik Hata",
    nextAction: "Çalıştırmayı aç",
  },
  {
    id: "ALT-SYN-1038",
    title: "Ölçüm kapsamı politika hedefinin altında",
    scope: "Sentetik Dataset C · Kapsam %82",
    time: "46 dk",
    tone: "warning",
    statusLabel: "Uyarı",
    nextAction: "Koşulları gör",
  },
];

export const syntheticDashboardViewModel: DashboardViewModel = {
  kpis,
  trendObservations,
  alerts,
  fieldScores: syntheticFieldScores,
  qualityDimensionRows: syntheticQualityDimensionRows,
  dataNotice: "Bu ekran yalnız sentetik gösterim verisi kullanır; üretim API'si, kullanıcı oturumu veya banka verisi bağlı değildir.",
  trendDescription: "Son 30 UTC gün · yalnız resmî skorlar",
  measurementNote: "Son sonuç sınırlı kapsama rağmen onaylı sentetik politika koşullarını karşılıyor. Provizyonel 13 Temmuz sonucu resmî trend ve SLA hesabına katılmadı; önceki resmî skor geçersiz kılınmadı.",
};

export function dashboardViewModelFromApi(
  response: DashboardSummaryApiResponse,
): DashboardViewModel {
  const scopeKey = selectScopeKey(response.periods);
  const observations = response.periods.map((period) => {
    const observation = period.observations.find((item) => observationScopeKey(item) === scopeKey);
    const score = parseScore(observation?.score_value ?? null);
    const isTechnical = observation?.score_status === "NOT_CALCULATED_TECHNICAL_ERROR";
    const isOfficial = observation?.score_status === "CALCULATED" || observation?.score_status === "PARTIAL";
    return {
      date: period.period_start.slice(0, 10),
      displayDate: formatUtcDate(period.period_start),
      rawScore: null,
      finalScore: score,
      qualification: "Bu API diliminde sağlanmıyor",
      usageDecision: "Bu API diliminde sağlanmıyor",
      coverageRate: null,
      technicalStatus: isTechnical ? "Teknik Hata" as const : observation ? "Başarılı" as const : "Hesaplanmadı" as const,
      official: isOfficial && score !== null,
    };
  });
  const latest = [...response.periods]
    .reverse()
    .flatMap((period) => period.observations)
    .find((item) => observationScopeKey(item) === scopeKey);
  const latestScore = parseScore(latest?.score_value ?? null);
  const latestTone = scoreTone(latest?.score_status);
  const scopeLabel = scopeKey === "ENTERPRISE:" ? "Kurum kapsamı" : `Kaynak kapsamı: ${scopeKey.split(":", 2)[1] ?? "—"}`;

  return {
    kpis: [
      {
        id: "quality-score",
        label: "Nihai Kalite Skoru",
        value: formatScore(latestScore),
        detail: latest ? `${scopeLabel} · ${formatUtcDateTime(latest.calculated_at)}` : "Yetkili kapsamda resmî skor bulunamadı",
        tone: latestTone,
        statusLabel: scoreStatusLabel(latest?.score_status),
      },
      measurementQualificationKpi(response.operational_indicators),
      criticalControlKpi(response.operational_indicators),
      technicalErrorKpi(response.operational_indicators),
    ],
    trendObservations: observations,
    alerts: [],
    fieldScores: response.data_origin === "synthetic-development" ? syntheticFieldScores : [],
    qualityDimensionRows: response.data_origin === "synthetic-development" ? syntheticQualityDimensionRows : [],
    dataNotice: response.data_origin === "synthetic-development"
      ? "Yerel dashboard API'si sentetik geliştirme skorlarıyla bağlıdır; üretim oturumu veya banka verisi kullanılmaz."
      : "Dashboard verisi yetkili API kapsamından yüklenmiştir.",
    trendDescription: `Son 30 UTC gün · ${scopeLabel} · yalnız resmî skorlar`,
    measurementNote: "Ölçüm yeterliliği ve teknik sağlık 21C operasyonel göstergelerinden alınır. Kapsam, kullanım kararı, kritik kontrol sonuçları ve alarm akışı ilgili runtime sözleşmeleri tamamlanmadan üretilmez.",
  };
}

function selectScopeKey(periods: DashboardApiPeriod[]): string {
  const keys = periods.flatMap((period) => period.observations.map(observationScopeKey));
  return keys.includes("ENTERPRISE:") ? "ENTERPRISE:" : [...keys].sort()[0] ?? "ENTERPRISE:";
}

function observationScopeKey(observation: DashboardApiObservation): string {
  return `${observation.scope_type}:${observation.scope_id ?? ""}`;
}

function parseScore(value: string | number | null): number | null {
  if (value === null) return null;
  const score = typeof value === "number" ? value : Number(value);
  return Number.isFinite(score) ? score : null;
}

function formatScore(value: number | null): string {
  return value === null ? "—" : value.toLocaleString("tr-TR", { maximumFractionDigits: 2 });
}

function formatUtcDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(value));
}

function formatUtcDateTime(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(value));
}

function measurementQualificationKpi(
  indicators: DashboardOperationalIndicatorsApiResponse,
): KpiViewModel {
  const qualification = indicators.measurement_qualification;
  if (qualification.status === "TECHNICAL_FAILURE") {
    return {
      id: "qualification",
      label: "Ölçüm Yeterliliği",
      value: "—",
      detail: `${qualification.evaluated_scope_count} kapsam değerlendirildi · kalite skoru sıfırlanmadı`,
      tone: "technical",
      statusLabel: "Teknik Başarısızlık",
    };
  }
  if (qualification.status === "VALIDATION_REQUIRED") {
    return {
      id: "qualification",
      label: "Ölçüm Yeterliliği",
      value: "İnceleme",
      detail: `${qualification.evaluated_scope_count} kapsam · aktif yeterlilik politikası bulunamadı`,
      tone: "warning",
      statusLabel: "Doğrulama Gerekli",
    };
  }
  return unavailableKpi("qualification", "Ölçüm Yeterliliği", "Yetkili kapsamda ölçüm bulunamadı");
}

function criticalControlKpi(
  indicators: DashboardOperationalIndicatorsApiResponse,
): KpiViewModel {
  const controls = indicators.critical_controls;
  if (controls.status === "NOT_AVAILABLE") {
    return unavailableKpi(
      "critical-rules",
      "Kritik Kontroller",
      "Kritik kural sonuç kaynağı henüz bağlı değil",
    );
  }
  return unavailableKpi("critical-rules", "Kritik Kontroller", "Kritik kontrol sonucu bulunamadı");
}

function technicalErrorKpi(
  indicators: DashboardOperationalIndicatorsApiResponse,
): KpiViewModel {
  const technical = indicators.technical_errors;
  if (technical.observation_count === 0) {
    return {
      id: "technical-errors",
      label: "Teknik Hatalar",
      value: "0",
      detail: "Son 30 UTC günlük yetkili kapsamda teknik hata yok",
      tone: "success",
      statusLabel: "Teknik Hata Yok",
    };
  }
  const lastOccurred = technical.last_occurred_at
    ? formatUtcDateTime(technical.last_occurred_at)
    : "zaman bilgisi yok";
  return {
    id: "technical-errors",
    label: "Teknik Hatalar",
    value: String(technical.observation_count),
    detail: `${technical.execution_count} çalıştırma · ${technical.affected_source_count} kaynak · son olay ${lastOccurred}`,
    tone: "technical",
    statusLabel: "Teknik Hata",
  };
}

function unavailableKpi(id: string, label: string, detail: string): KpiViewModel {
  return {
    id,
    label,
    value: "—",
    detail,
    tone: "unknown",
    statusLabel: "Veri Yok",
  };
}

function dimensionCell(dimension: string, score: number | null): QualityDimensionCellViewModel {
  if (score === null) {
    return { dimension, score, tone: "unknown", statusLabel: "Hesaplanmadı" };
  }
  if (score < 70) {
    return { dimension, score, tone: "critical", statusLabel: "Kritik" };
  }
  if (score < 85) {
    return { dimension, score, tone: "warning", statusLabel: "Riskli" };
  }
  return { dimension, score, tone: "success", statusLabel: "Yeterli" };
}

function scoreTone(status: string | undefined): StatusTone {
  if (status === "NOT_CALCULATED_TECHNICAL_ERROR") return "technical";
  if (status === "CALCULATED") return "success";
  if (status === "PARTIAL") return "warning";
  return "unknown";
}

function scoreStatusLabel(status: string | undefined): string {
  const labels: Record<string, string> = {
    CALCULATED: "Hesaplandı",
    PARTIAL: "Kısmi",
    NO_DATA: "Veri Yok",
    NOT_CALCULATED: "Hesaplanmadı",
    NOT_CALCULATED_TECHNICAL_ERROR: "Teknik Hata",
    CONFIG_ERROR: "Yapılandırma Hatası",
  };
  return status ? labels[status] ?? "Bilinmiyor" : "Veri Yok";
}
