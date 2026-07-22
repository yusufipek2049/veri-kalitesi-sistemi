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
