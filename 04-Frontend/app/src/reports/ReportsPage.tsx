import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Skeleton,
  TextField,
  Typography,
} from "@mui/material";
import {
  CheckCircle2,
  CircleSlash2,
  FileChartColumn,
  RefreshCw,
  Search,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens, type StatusTone } from "../theme/tokens";
import {
  syntheticReportSummary,
  type ReportState,
  type ReportSummary,
  type ReportSummaryRow,
} from "./model";

interface ReportsPageProps {
  state?: ReportState;
  summary?: ReportSummary;
  correlationId?: string;
  onRefresh?: () => void;
}

const statusLabels: Record<string, string> = {
  CALCULATED: "Hesaplandı",
  PARTIAL: "Kısmi",
  NO_DATA: "Veri yok",
  NOT_CALCULATED: "Hesaplanmadı",
  NOT_CALCULATED_TECHNICAL_ERROR: "Teknik hata",
  CONFIG_ERROR: "Yapılandırma hatası",
};

const levelLabels: Record<string, string> = {
  GOOD: "İyi",
  ACCEPTABLE: "Kabul edilebilir",
  RISKY: "Riskli",
  CRITICAL: "Kritik",
};

function statusPresentation(status: string): {
  icon: LucideIcon;
  tone: StatusTone;
} {
  if (status === "CALCULATED") return { icon: CheckCircle2, tone: "success" };
  if (status === "PARTIAL") return { icon: FileChartColumn, tone: "warning" };
  if (status === "NOT_CALCULATED_TECHNICAL_ERROR" || status === "CONFIG_ERROR") {
    return { icon: Wrench, tone: "technical" };
  }
  return { icon: CircleSlash2, tone: "unknown" };
}

function levelTone(level: string | null): StatusTone {
  if (level === "GOOD") return "success";
  if (level === "ACCEPTABLE") return "info";
  if (level === "RISKY") return "warning";
  if (level === "CRITICAL") return "critical";
  return "unknown";
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatScore(value: number | null): string {
  return value === null
    ? "—"
    : new Intl.NumberFormat("tr-TR", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(value);
}

function SummaryMetric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <Paper component="section" sx={{ borderRadius: 1.5, minHeight: 116, p: 4 }} variant="outlined">
      <Typography color="text.secondary" variant="body2">{label}</Typography>
      <Typography sx={{ mt: 2 }} variant="h2">{value}</Typography>
      <Typography color="text.secondary" variant="caption">{detail}</Typography>
    </Paper>
  );
}

function ReportRow({ row }: { row: ReportSummaryRow }) {
  const presentation = statusPresentation(row.scoreStatus);
  const Icon = presentation.icon;
  return (
    <Box
      component="li"
      sx={{
        alignItems: "center",
        borderBottom: 1,
        borderColor: "divider",
        display: "grid",
        gap: 3,
        gridTemplateColumns: {
          xs: "40px minmax(0, 1fr)",
          md: "40px minmax(220px, 1fr) minmax(120px, .5fr) minmax(145px, .6fr)",
          lg: "40px minmax(240px, 1fr) minmax(120px, .5fr) minmax(145px, .6fr) minmax(155px, .65fr) minmax(185px, .75fr)",
        },
        minHeight: 88,
        px: 4,
        py: 3,
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Box
        aria-hidden="true"
        data-testid="report-icon-slot"
        sx={(theme) => ({
          alignItems: "center",
          bgcolor: theme.status[`${presentation.tone}Surface`],
          borderRadius: 1,
          color: theme.status[presentation.tone],
          display: "flex",
          height: 40,
          justifyContent: "center",
          width: 40,
        })}
      >
        <Icon size={designTokens.layout.navIconSize} strokeWidth={1.8} />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography noWrap sx={{ fontWeight: 700 }}>{row.sourceId}</Typography>
        <Typography color="text.secondary" variant="caption">Yetkili veri kaynağı</Typography>
      </Box>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" } }}>
        <Typography color="text.secondary" sx={{ display: { xs: "block", lg: "none" } }} variant="caption">Skor</Typography>
        <Typography sx={{ fontWeight: 700 }}>{formatScore(row.scoreValue)}</Typography>
      </Box>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" } }}>
        <StatusBadge
          label={statusLabels[row.scoreStatus] ?? row.scoreStatus}
          tone={presentation.tone}
        />
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" } }}>
        <StatusBadge
          label={row.level ? levelLabels[row.level] ?? row.level : "Seviye yok"}
          tone={levelTone(row.level)}
        />
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" } }}>
        <Typography variant="body2">{formatDate(row.calculatedAt)}</Typography>
        <Typography color="text.secondary" variant="caption">Son rapor gözlemi</Typography>
      </Box>
    </Box>
  );
}

function StateMessage({
  state,
  correlationId,
  onRefresh,
}: Pick<ReportsPageProps, "correlationId" | "onRefresh"> & {
  state: "empty" | "error" | "unauthorized";
}) {
  const content = {
    empty: ["Rapor verisi bulunamadı", "Yetkili kapsamda son 30 güne ait resmî gözlem yok."],
    error: ["Rapor önizlemesi yüklenemedi", `Teknik bir sorun oluştu. Yeniden deneyin. İzleme kodu: ${correlationId ?? "bulunamadı"}.`],
    unauthorized: ["Bu görünüm için yetkiniz yok", "Rapor kapsamı ve özet değerleri gösterilmedi."],
  }[state];
  return (
    <Alert
      action={state === "error" ? <Button color="inherit" onClick={onRefresh}>Yeniden dene</Button> : undefined}
      severity={state === "error" ? "error" : state === "unauthorized" ? "warning" : "info"}
    >
      <Typography sx={{ fontWeight: 700 }}>{content[0]}</Typography>
      <Typography variant="body2">{content[1]}</Typography>
    </Alert>
  );
}

export function ReportsPage({
  state = "normal",
  summary = syntheticReportSummary,
  correlationId,
  onRefresh,
}: ReportsPageProps) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [level, setLevel] = useState("ALL");
  const visibleRows = useMemo(
    () => summary.rows.filter((row) => (
      row.sourceId.toLocaleLowerCase("tr-TR").includes(query.toLocaleLowerCase("tr-TR"))
      && (status === "ALL" || row.scoreStatus === status)
      && (level === "ALL" || row.level === level)
    )),
    [level, query, status, summary.rows],
  );
  const effectiveRows = state === "long-content"
    ? Array.from({ length: 6 }, (_, group) => summary.rows.map((row) => ({
        ...row,
        sourceId: `${row.sourceId}-${group + 1}`,
      }))).flat()
    : visibleRows;
  const resetFilters = () => {
    setQuery("");
    setStatus("ALL");
    setLevel("ALL");
  };

  return (
    <AppShell currentPage="Raporlar">
      <Box sx={(theme) => ({ display: "grid", gap: 5, margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 4, lg: 6 }, width: "100%" })}>
        <Box sx={{ alignItems: { md: "center" }, display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, justifyContent: "space-between" }}>
          <Box>
            <Typography component="h1" variant="h1">Raporlar</Typography>
            <Typography color="text.secondary">Yetkili kaynaklarınızdaki toplulaştırılmış 30 günlük rapor önizlemesi</Typography>
          </Box>
          {state !== "unauthorized" ? <Button onClick={onRefresh} startIcon={<RefreshCw aria-hidden="true" size={16} />} variant="contained">Yenile</Button> : null}
        </Box>

        {state !== "unauthorized" ? (
          <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
            <Box aria-label="Rapor filtreleri" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(180px, 1fr))", lg: "minmax(230px, 1.3fr) repeat(4, minmax(145px, .7fr))" } }}>
              <TextField label="Kaynak ara" onChange={(event) => setQuery(event.target.value)} slotProps={{ input: { startAdornment: <Search aria-hidden="true" size={16} /> } }} value={query} />
              <FormControl><InputLabel id="report-status-label">Sonuç durumu</InputLabel><Select label="Sonuç durumu" labelId="report-status-label" onChange={(event) => setStatus(event.target.value)} value={status}><MenuItem value="ALL">Tüm durumlar</MenuItem>{Object.entries(statusLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <FormControl><InputLabel id="report-level-label">Skor seviyesi</InputLabel><Select label="Skor seviyesi" labelId="report-level-label" onChange={(event) => setLevel(event.target.value)} value={level}><MenuItem value="ALL">Tüm seviyeler</MenuItem>{Object.entries(levelLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <FormControl><InputLabel id="report-period-label">Dönem</InputLabel><Select disabled label="Dönem" labelId="report-period-label" value="LAST_30_DAYS"><MenuItem value="LAST_30_DAYS">Son 30 gün</MenuItem></Select></FormControl>
              <FormControl><InputLabel id="report-scope-label">Kapsam</InputLabel><Select disabled label="Kapsam" labelId="report-scope-label" value="AUTHORIZED"><MenuItem value="AUTHORIZED">Yetkili kapsam</MenuItem></Select></FormControl>
            </Box>
            <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 3 }}>
              <Button onClick={resetFilters} size="small">Filtreleri temizle</Button>
            </Box>
          </Paper>
        ) : null}

        {state === "loading" ? <Box aria-busy="true" aria-label="Rapor önizlemesi yükleniyor">{Array.from({ length: 6 }, (_, index) => <Skeleton height={88} key={index} />)}</Box> : null}
        {state === "empty" || state === "error" || state === "unauthorized" ? <StateMessage correlationId={correlationId} onRefresh={onRefresh} state={state} /> : null}

        {(state === "normal" || state === "long-content") ? (
          <>
            <Box aria-label="Rapor özeti" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" } }}>
              <SummaryMetric detail="Kısmi resmî sonuçlar dahil" label="Ortalama kalite skoru" value={formatScore(summary.averageScore)} />
              <SummaryMetric detail={`${summary.sourceCount - summary.calculatedSourceCount} hesaplanamayan`} label="Hesaplanan kaynak" value={`${summary.calculatedSourceCount} / ${summary.sourceCount}`} />
              <SummaryMetric detail={`Politika: ${summary.policyVersion}`} label="Veri koruma" value={summary.maskingMode === "AGGREGATED_ONLY" ? "Toplulaştırılmış" : summary.maskingMode} />
            </Box>

            {effectiveRows.length === 0 ? <StateMessage state="empty" /> : (
              <Paper component="section" sx={{ borderRadius: 1.5, overflow: "hidden" }} variant="outlined">
                <Box sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
                  <Box>
                    <Typography component="h2" variant="h3">Kaynak Skor Özeti</Typography>
                    <Typography color="text.secondary" variant="caption">{formatDate(summary.periodStart)} – {formatDate(summary.periodEnd)}</Typography>
                  </Box>
                  <Typography color="text.secondary" variant="body2">{effectiveRows.length} kaynak</Typography>
                </Box>
                <Box aria-hidden="true" sx={{ borderBottom: 1, borderColor: "divider", color: "text.secondary", display: { xs: "none", lg: "grid" }, fontSize: "caption.fontSize", fontWeight: 700, gap: 3, gridTemplateColumns: "40px minmax(240px, 1fr) minmax(120px, .5fr) minmax(145px, .6fr) minmax(155px, .65fr) minmax(185px, .75fr)", px: 4, py: 2 }}>
                  <Box /><Box>Veri kaynağı</Box><Box>Skor</Box><Box>Sonuç durumu</Box><Box>Seviye</Box><Box>Ölçüm zamanı</Box>
                </Box>
                <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>{effectiveRows.map((row) => <ReportRow key={row.sourceId} row={row} />)}</Box>
              </Paper>
            )}
          </>
        ) : null}
      </Box>
    </AppShell>
  );
}
