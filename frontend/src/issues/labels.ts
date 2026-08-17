export const statusLabels: Record<string, string> = {
  NEW: "Yeni",
  ASSIGNED: "Atandı",
  INVESTIGATING: "İnceleniyor",
  WAITING_FOR_RESOLUTION: "Çözüm bekliyor",
  RESOLVED: "Çözüldü",
  VERIFIED: "Doğrulandı",
  CLOSED: "Kapatıldı",
  CANCELLED: "İptal edildi",
};

export const priorityLabels: Record<string, string> = {
  LOW: "Düşük",
  MEDIUM: "Orta",
  HIGH: "Yüksek",
  CRITICAL: "Kritik",
};

export const triggerLabels: Record<string, string> = {
  QUALITY_THRESHOLD: "Kalite eşiği",
  CRITICAL_RULE_FAILURE: "Kritik kontrol",
  TECHNICAL_ERROR: "Teknik olay",
  MANUAL: "Manuel",
};

export interface IssueActionFeedback {
  severity: "success" | "error";
  message: string;
}

export function localDateTimeValue(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
}
