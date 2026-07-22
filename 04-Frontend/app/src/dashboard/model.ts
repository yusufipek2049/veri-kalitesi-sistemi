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

export interface DashboardViewModel {
  kpis: KpiViewModel[];
  trendObservations: TrendObservation[];
  alerts: AlertViewModel[];
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

export interface DashboardSummaryApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  as_of: string;
  has_data: boolean;
  periods: DashboardApiPeriod[];
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
      unavailableKpi("qualification", "Ölçüm Yeterliliği"),
      unavailableKpi("critical-rules", "Kritik Kontroller"),
      unavailableKpi("technical-errors", "Teknik Hatalar"),
    ],
    trendObservations: observations,
    alerts: [],
    dataNotice: response.data_origin === "synthetic-development"
      ? "Yerel dashboard API'si sentetik geliştirme skorlarıyla bağlıdır; üretim oturumu veya banka verisi kullanılmaz."
      : "Dashboard verisi yetkili API kapsamından yüklenmiştir.",
    trendDescription: `Son 30 UTC gün · ${scopeLabel} · yalnız resmî skorlar`,
    measurementNote: "Bu ilk API dilimi yalnız mevcut resmî skor ve trend alanlarını taşır. Ölçüm yeterliliği, kapsam, kullanım kararı ve alarm akışı sonraki sözleşmeler tamamlanmadan üretilmez.",
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

function unavailableKpi(id: string, label: string): KpiViewModel {
  return {
    id,
    label,
    value: "—",
    detail: "Bu API diliminde sağlanmıyor",
    tone: "unknown",
    statusLabel: "Veri Yok",
  };
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
