import type { DashboardOverview } from "./model";

type TrendPeriods = DashboardOverview["trend"]["periods"];

interface TooltipColors {
  critical: string;
  success: string;
  muted: string;
  chipBackground: string;
}

interface TooltipItem {
  dataIndex: number;
  seriesId?: string;
  seriesName?: string;
}

const sourceSeriesPrefix = "source:";

const statusLabel: Record<string, string> = {
  CALCULATED: "Hesaplandı",
  NOT_CALCULATED: "Hesaplanmadı",
  NO_DATA: "Veri yok",
  PARTIAL: "Kısmi",
  NOT_CALCULATED_TECHNICAL_ERROR: "Teknik hata",
  CONFIG_ERROR: "Yapılandırma hatası",
};

const comparisonLabel: Record<string, string> = {
  COMPARABLE: "Karşılaştırılabilir",
  NOT_COMPARABLE: "Karşılaştırılamaz",
  UNKNOWN: "Belirsiz",
};

const shortDateFormatter = new Intl.DateTimeFormat("tr-TR", {
  day: "2-digit",
  month: "2-digit",
});

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatShortDate(value: string): string {
  const parts = shortDateFormatter.formatToParts(new Date(value));
  const day = parts.find((part) => part.type === "day")?.value ?? "";
  const month = parts.find((part) => part.type === "month")?.value ?? "";
  return `${day}.${month}`;
}

function formatTooltipChange(value: number | null): string {
  if (value === null) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}`;
}

export function createTrendTooltipFormatter(
  periods: TrendPeriods,
  colors: TooltipColors,
  sourceNames: ReadonlyMap<string, string> = new Map(),
) {
  return (params: unknown): string => {
    const items = params as TooltipItem[];
    if (!Array.isArray(items) || items.length === 0) return "";

    const period = periods[items[0].dataIndex];
    if (!period) return "";

    const observation = period.observations.find((item) => item.scopeType === "ENTERPRISE");
    const score = observation?.scoreValue ?? null;
    const level = observation?.level ?? null;
    const scoreStatus = observation?.scoreStatus ?? "NO_DATA";
    const change = observation?.change ?? null;
    const comparisonStatus = observation?.comparisonStatus ?? "UNKNOWN";
    const reasonCodes = observation?.comparisonReasonCodes ?? [];
    const changeColor = change === null
      ? colors.muted
      : change >= 0
        ? colors.success
        : colors.critical;
    const levelChip = level
      ? `<span style="background:${escapeHtml(colors.chipBackground)};border-radius:10px;display:inline-block;font-size:11px;margin-left:6px;padding:1px 7px">${escapeHtml(level)}</span>`
      : "";
    const reasons = reasonCodes.length > 0
      ? ` <span style="color:${escapeHtml(colors.muted)}">(${reasonCodes.map(escapeHtml).join(", ")})</span>`
      : "";

    const lines = [
      '<div data-testid="trend-tooltip" style="min-width:220px">',
      `<div style="font-weight:600;margin-bottom:6px">${formatShortDate(period.periodStart)} – ${formatShortDate(period.periodEnd)}</div>`,
      `<div>Skor: <strong>${score === null ? "—" : score.toFixed(1)}</strong>${levelChip}</div>`,
      `<div>Durum: ${escapeHtml(statusLabel[scoreStatus] ?? scoreStatus)}</div>`,
      `<div>Değişim: <strong style="color:${escapeHtml(changeColor)}">${formatTooltipChange(change)}</strong></div>`,
    ];

    const movingAverage = observation?.trend?.movingAverage;
    if (movingAverage !== null && movingAverage !== undefined) {
      lines.push(`<div>Hareketli Ortalama: ${movingAverage.toFixed(1)}</div>`);
    }

    for (const item of items) {
      if (!item.seriesId?.startsWith(sourceSeriesPrefix)) continue;
      const sourceId = item.seriesId.slice(sourceSeriesPrefix.length);
      const sourceObservation = period.observations.find(
        (candidate) => candidate.scopeType === "SOURCE" && candidate.scopeId === sourceId,
      );
      const sourceName = sourceNames.get(sourceId) ?? item.seriesName ?? sourceId;
      lines.push(
        `<div style="color:${escapeHtml(colors.muted)}">${escapeHtml(sourceName)}: ${sourceObservation?.scoreValue == null ? "—" : sourceObservation.scoreValue.toFixed(1)}</div>`,
      );
    }

    if (observation?.versionBoundary) {
      const version = observation.policyVersion ? `: ${escapeHtml(observation.policyVersion)}` : "";
      lines.push(`<div style="color:${escapeHtml(colors.muted)}">Sürüm değişimi${version}</div>`);
    }

    lines.push(`<div>Karşılaştırma: ${escapeHtml(comparisonLabel[comparisonStatus] ?? comparisonStatus)}${reasons}</div>`);
    lines.push("</div>");
    return lines.join("");
  };
}
