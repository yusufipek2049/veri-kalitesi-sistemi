import {
  Activity,
  Braces,
  CheckCircle,
  Clock3,
  FilePen,
  KeyRound,
  ListChecks,
  ScanText,
  SendHorizontal,
  ThumbsUp,
  Undo2,
  PowerOff,
  type LucideIcon,
} from "lucide-react";
import type { RuleAction } from "./model";

export const statusLabels: Record<string, string> = {
  DRAFT: "Taslak",
  ACTIVE: "Aktif",
  PASSIVE: "Pasif",
  REVIEW_REQUIRED: "İnceleme gerekli",
  ARCHIVED: "Arşivlendi",
};

export const dimensionLabels: Record<string, string> = {
  COMPLETENESS: "Tamlık",
  ACCURACY: "Doğruluk",
  VALIDITY: "Geçerlilik",
  CONSISTENCY: "Tutarlılık",
  UNIQUENESS: "Tekillik",
  TIMELINESS: "Güncellik",
  INTEGRITY: "Bütünlük",
};

export const criticalityLabels: Record<string, string> = {
  LOW: "Düşük",
  MEDIUM: "Orta",
  HIGH: "Yüksek",
  CRITICAL: "Kritik",
};

export const ruleTypeLabels: Record<string, string> = {
  REQUIRED: "Zorunluluk",
  UNIQUE: "Tekillik",
  RANGE: "Aralık",
  REGEX: "Desen",
  FRESHNESS: "Güncellik",
  REFERENTIAL_INTEGRITY: "Referans bütünlüğü",
  CROSS_TABLE_CONSISTENCY: "Tablolar arası tutarlılık",
  CUSTOM_SQL: "Özel SQL",
};

export const actionLabels: Record<RuleAction, string> = {
  CREATE_VERSION: "Sürüm Oluştur",
  TEST_RULE: "Test Et",
  ACTIVATE: "Aktifleştir",
  REQUEST_APPROVAL: "Onaya Gönder",
  DECIDE_APPROVAL: "Onayla/Reddet",
  WITHDRAW_APPROVAL: "Onayı Geri Çek",
  PASSIVATE: "Pasifleştir",
};

export const actionIcons: Record<RuleAction, LucideIcon> = {
  CREATE_VERSION: FilePen,
  TEST_RULE: Activity,
  ACTIVATE: CheckCircle,
  REQUEST_APPROVAL: SendHorizontal,
  DECIDE_APPROVAL: ThumbsUp,
  WITHDRAW_APPROVAL: Undo2,
  PASSIVATE: PowerOff,
};

const ruleTypeIcons: Record<string, LucideIcon> = {
  FRESHNESS: Clock3,
  REFERENTIAL_INTEGRITY: KeyRound,
  REGEX: ScanText,
  CUSTOM_SQL: Braces,
};

export function ruleIcon(ruleType: string): LucideIcon {
  return ruleTypeIcons[ruleType] ?? ListChecks;
}

export function statusTone(status: string): "success" | "warning" | "unknown" {
  if (status === "ACTIVE") return "success";
  if (status === "REVIEW_REQUIRED") return "warning";
  return "unknown";
}

export function criticalityTone(
  criticality: string,
): "critical" | "warning" | "info" | "unknown" {
  if (criticality === "CRITICAL") return "critical";
  if (criticality === "HIGH") return "warning";
  if (criticality === "MEDIUM") return "info";
  return "unknown";
}
