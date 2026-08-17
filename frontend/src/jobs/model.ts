/**
 * Jobs (zamanlayıcı) modülü modelleri.
 * Backend Schedule ve schedule-proposals yanıtlarının frontend karşılığıdır.
 */

export type JobState = "normal" | "loading" | "empty" | "error" | "unauthorized";

export type TimelinessNature = "NEAR_TIME" | "REAL_TIME" | "BATCH_TIME";

export type ScheduleType = "ONCE" | "DAILY" | "WEEKLY" | "MONTHLY" | "INTERVAL";

export interface JobItem {
  id: string;
  name: string;
  scheduleType: ScheduleType;
  timezoneName: string;
  ruleVersionIds: string[];
  createdBy: string;
  localTime: string | null;
  dayOfWeek: number | null;
  dayOfMonth: number | null;
  intervalMinutes: number | null;
  isActive: boolean;
  nextRunAt: string | null;
  createdAt: string;
  lastTriggeredAt: string | null;
}

export interface ScheduleProposal {
  scheduleType: ScheduleType;
  intervalMinutes: number | null;
  label: string;
}

export interface ScheduleApiItem {
  schedule_id: string;
  name: string;
  schedule_type: ScheduleType;
  timezone_name: string;
  rule_version_ids: string[];
  created_by: string;
  local_time: string | null;
  day_of_week: number | null;
  day_of_month: number | null;
  interval_minutes: number | null;
  is_active: boolean;
  next_run_at: string | null;
  created_at: string;
  last_triggered_at: string | null;
}

interface ApiEnvelope {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
}

export interface ScheduleListApiResponse extends ApiEnvelope {
  items: ScheduleApiItem[];
}

export interface ScheduleCreatedApiResponse extends ScheduleApiItem, ApiEnvelope {
  preview_runs: string[];
}

export interface ScheduleProposalApiResponse extends ApiEnvelope {
  dataset_id: string;
  timeliness_nature: TimelinessNature | null;
  band: string | null;
  proposals: Array<{
    schedule_type: ScheduleType;
    interval_minutes: number | null;
    label: string;
  }>;
}

export interface ScheduleCreatePayload {
  name: string;
  dataset_id: string;
  schedule_type: ScheduleType;
  timezone_name: string;
  rule_version_ids: string[];
  local_time?: string;
  day_of_week?: number;
  day_of_month?: number;
  interval_minutes?: number;
}

export const timelinessNatureLabels: Record<TimelinessNature, string> = {
  NEAR_TIME: "Yakın Zamanlı",
  REAL_TIME: "Anlık",
  BATCH_TIME: "Toplu (Batch)",
};

export const scheduleTypeLabels: Record<ScheduleType, string> = {
  ONCE: "Tek Seferlik",
  DAILY: "Günlük",
  WEEKLY: "Haftalık",
  MONTHLY: "Aylık",
  INTERVAL: "Aralıklı",
};

const WEEKDAY_LABELS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"];

/** Zamanlayıcı tanımını insan okunur özet metne çevirir. */
export function scheduleSummary(item: JobItem): string {
  if (item.scheduleType === "INTERVAL" && item.intervalMinutes !== null) {
    if (item.intervalMinutes === 1) return "Anlık (1 dakikada bir)";
    return `${item.intervalMinutes} dakikada bir`;
  }
  const time = item.localTime ? item.localTime.slice(0, 5) : null;
  if (item.scheduleType === "DAILY") return time ? `Her gün ${time}` : "Her gün";
  if (item.scheduleType === "WEEKLY") {
    const day = item.dayOfWeek !== null ? WEEKDAY_LABELS[item.dayOfWeek] ?? "" : "";
    return time ? `Haftalık · ${day} ${time}` : `Haftalık · ${day}`;
  }
  if (item.scheduleType === "MONTHLY") {
    return time ? `Aylık · ${item.dayOfMonth}. gün ${time}` : `Aylık · ${item.dayOfMonth}. gün`;
  }
  return scheduleTypeLabels[item.scheduleType];
}

export function jobFromApi(item: ScheduleApiItem): JobItem {
  return {
    id: item.schedule_id,
    name: item.name,
    scheduleType: item.schedule_type,
    timezoneName: item.timezone_name,
    ruleVersionIds: item.rule_version_ids,
    createdBy: item.created_by,
    localTime: item.local_time,
    dayOfWeek: item.day_of_week,
    dayOfMonth: item.day_of_month,
    intervalMinutes: item.interval_minutes,
    isActive: item.is_active,
    nextRunAt: item.next_run_at,
    createdAt: item.created_at,
    lastTriggeredAt: item.last_triggered_at,
  };
}

export function jobsFromApi(response: ScheduleListApiResponse): JobItem[] {
  return response.items.map(jobFromApi);
}

export function scheduleProposalsFromApi(
  response: ScheduleProposalApiResponse,
): ScheduleProposal[] {
  return response.proposals.map((proposal) => ({
    scheduleType: proposal.schedule_type,
    intervalMinutes: proposal.interval_minutes,
    label: proposal.label,
  }));
}
