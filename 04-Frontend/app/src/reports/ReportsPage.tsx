import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Skeleton,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import {
  Calendar,
  CheckCircle2,
  CircleSlash2,
  Clock,
  Download,
  FileChartColumn,
  FileDown,
  FileText,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens, type StatusTone } from "../theme/tokens";
import {
  syntheticReportSummary,
  syntheticSchedules,
  type ReportFormat,
  type ReportItem,
  type ReportRequest,
  type ReportSchedule,
  type ReportScheduleCreateRequest,
  type ReportState,
  type ReportStatus,
  type ReportSummary,
  type ReportSummaryRow,
  type ReportType,
} from "./model";

interface ReportsPageProps {
  state?: ReportState;
  summary?: ReportSummary;
  reportItems?: ReportItem[];
  scheduleItems?: ReportSchedule[];
  correlationId?: string;
  onRefresh?: () => void;
  onCreateReport?: (request: ReportRequest) => Promise<void>;
  onDownloadReport?: (reportId: string, filename: string) => Promise<void>;
  onCreateSchedule?: (request: ReportScheduleCreateRequest) => Promise<void>;
  onDeleteSchedule?: (scheduleId: string) => Promise<void>;
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

const reportStatusLabels: Record<ReportStatus, string> = {
  QUEUED: "Sırada",
  RUNNING: "Oluşturuluyor",
  READY: "Hazır",
  FAILED: "Başarısız",
  EXPIRED: "Süresi doldu",
};

const reportTypeLabels: Record<string, string> = {
  SUMMARY: "Özet",
  DETAIL: "Detay",
  TREND: "Trend",
  UNIT: "Birim",
  OWNER: "Sahip",
  CRITICAL_DATA: "Kritik Veri",
  ISSUE_PERFORMANCE: "Sorun Performansı",
};

const formatLabels: Record<ReportFormat, string> = {
  PDF: "PDF",
  XLSX: "Excel (XLSX)",
  CSV: "CSV",
};

const scheduleTypeLabels: Record<string, string> = {
  ONCE: "Tek seferlik",
  DAILY: "Günlük",
  WEEKLY: "Haftalık",
  MONTHLY: "Aylık",
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

function reportStatusPresentation(status: ReportStatus): {
  icon: LucideIcon;
  tone: StatusTone;
} {
  if (status === "READY") return { icon: CheckCircle2, tone: "success" };
  if (status === "RUNNING") return { icon: Clock, tone: "info" };
  if (status === "QUEUED") return { icon: Clock, tone: "unknown" };
  if (status === "FAILED") return { icon: CircleSlash2, tone: "critical" };
  return { icon: CircleSlash2, tone: "unknown" };
}

function formatIcon(fmt: ReportFormat): LucideIcon {
  if (fmt === "PDF") return FileText;
  if (fmt === "XLSX") return FileChartColumn;
  return FileDown;
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

function ReportHistoryRow({
  item,
  onDownload,
}: {
  item: ReportItem;
  onDownload: (reportId: string, filename: string) => void;
}) {
  const presentation = reportStatusPresentation(item.status as ReportStatus);
  const Icon = presentation.icon;
  const FormatIcon = formatIcon(item.format as ReportFormat);
  const isReady = item.status === "READY" && item.expires_at && new Date(item.expires_at) > new Date();
  const isExpired = item.status === "EXPIRED" || (item.expires_at && new Date(item.expires_at) <= new Date());

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
          xs: "40px minmax(0, 1fr) auto",
          md: "40px minmax(180px, 1fr) minmax(100px, .4fr) minmax(120px, .5fr) auto",
        },
        minHeight: 72,
        px: 4,
        py: 2,
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Box
        aria-hidden="true"
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
        <Typography noWrap sx={{ fontWeight: 700 }}>
          {reportTypeLabels[item.report_type] ?? item.report_type}
        </Typography>
        <Typography color="text.secondary" variant="caption">
          {item.created_at ? formatDate(item.created_at) : "—"}
        </Typography>
      </Box>
      <Box>
        <FormatIcon aria-hidden="true" size={16} />
        <Typography color="text.secondary" sx={{ ml: 0.5 }} variant="caption">
          {formatLabels[item.format as ReportFormat] ?? item.format}
        </Typography>
      </Box>
      <Box>
        <StatusBadge
          label={reportStatusLabels[item.status as ReportStatus] ?? item.status}
          tone={isExpired ? "unknown" : presentation.tone}
        />
        {item.failure_reason && item.status === "FAILED" && (
          <Typography color="error" variant="caption">{item.failure_reason}</Typography>
        )}
      </Box>
      <Box>
        {isReady && (
          <Button
            onClick={() => onDownload(item.report_id, `report-${item.report_id.slice(0, 8)}.${item.format.toLowerCase()}`)}
            size="small"
            startIcon={<Download aria-hidden="true" size={14} />}
            variant="outlined"
          >
            İndir
          </Button>
        )}
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

function ReportRequestDialog({
  open,
  onClose,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (request: ReportRequest) => Promise<void>;
}) {
  const [reportType, setReportType] = useState<ReportType>("SUMMARY");
  const [format, setFormat] = useState<ReportFormat>("PDF");
  const [reasonCode, setReasonCode] = useState("");
  const [sensitivityLevel, setSensitivityLevel] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onSubmit({
        report_type: reportType,
        format,
        parameters: {},
        reason_code: reasonCode || "MANUAL_REQUEST",
        sensitivity_level: sensitivityLevel || null,
      });
      onClose();
      // Reset form
      setReportType("SUMMARY");
      setFormat("PDF");
      setReasonCode("");
      setSensitivityLevel("");
    } catch {
      // Error handled by parent
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      aria-describedby="report-request-dialog-description"
      aria-labelledby="report-request-dialog-title"
      maxWidth="sm"
      onClose={onClose}
      open={open}
      fullWidth
    >
      <DialogTitle id="report-request-dialog-title">Rapor Talebi</DialogTitle>
      <DialogContent id="report-request-dialog-description">
        <Box sx={{ display: "grid", gap: 3, pt: 2 }}>
          <FormControl fullWidth>
            <InputLabel id="report-type-label">Rapor türü</InputLabel>
            <Select
              label="Rapor türü"
              labelId="report-type-label"
              onChange={(e) => setReportType(e.target.value as ReportType)}
              value={reportType}
            >
              <MenuItem value="SUMMARY">Özet Rapor</MenuItem>
              <MenuItem value="DETAIL">Detay Rapor</MenuItem>
              <MenuItem value="TREND">Trend Raporu</MenuItem>
              <MenuItem value="UNIT">Birim Raporu</MenuItem>
              <MenuItem value="OWNER">Sahip Raporu</MenuItem>
              <MenuItem value="CRITICAL_DATA">Kritik Veri Raporu</MenuItem>
              <MenuItem value="ISSUE_PERFORMANCE">Sorun Performans Raporu</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel id="report-format-label">Format</InputLabel>
            <Select
              label="Format"
              labelId="report-format-label"
              onChange={(e) => setFormat(e.target.value as ReportFormat)}
              value={format}
            >
              <MenuItem value="PDF">PDF</MenuItem>
              <MenuItem value="XLSX">Excel (XLSX)</MenuItem>
              <MenuItem value="CSV">CSV</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Gerekçe kodu"
            onChange={(e) => setReasonCode(e.target.value)}
            placeholder="Örn: AYLIK_RAPOR, DENETIM, ANALIZ"
            value={reasonCode}
            fullWidth
          />
          <TextField
            label="Hassasiyet seviyesi (isteğe bağlı)"
            onChange={(e) => setSensitivityLevel(e.target.value)}
            placeholder="Örn: PUBLIC, INTERNAL, CONFIDENTIAL"
            value={sensitivityLevel}
            fullWidth
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button disabled={submitting} onClick={onClose}>İptal</Button>
        <Button
          disabled={submitting}
          onClick={handleSubmit}
          variant="contained"
        >
          {submitting ? "Talep ediliyor..." : "Raporu Talep Et"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function ScheduleRow({
  schedule,
  onDelete,
}: {
  schedule: ReportSchedule;
  onDelete: (schedule: ReportSchedule) => void;
}) {
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
          xs: "40px minmax(0, 1fr) auto",
          md: "40px minmax(180px, 1fr) minmax(100px, .4fr) minmax(100px, .4fr) minmax(140px, .5fr) auto",
        },
        minHeight: 72,
        px: 4,
        py: 2,
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Box
        aria-hidden="true"
        sx={(theme) => ({
          alignItems: "center",
          bgcolor: schedule.is_active ? theme.status.successSurface : theme.status.unknownSurface,
          borderRadius: 1,
          color: schedule.is_active ? theme.status.success : theme.status.unknown,
          display: "flex",
          height: 40,
          justifyContent: "center",
          width: 40,
        })}
      >
        <Calendar size={designTokens.layout.navIconSize} strokeWidth={1.8} />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography noWrap sx={{ fontWeight: 700 }}>{schedule.name}</Typography>
        <Typography color="text.secondary" variant="caption">
          {reportTypeLabels[schedule.report_type] ?? schedule.report_type}
        </Typography>
      </Box>
      <Box>
        <Typography variant="body2">{formatLabels[schedule.format as ReportFormat] ?? schedule.format}</Typography>
      </Box>
      <Box>
        <Typography variant="body2">{scheduleTypeLabels[schedule.schedule_type] ?? schedule.schedule_type}</Typography>
      </Box>
      <Box>
        <StatusBadge
          label={schedule.is_active ? "Aktif" : "Pasif"}
          tone={schedule.is_active ? "success" : "unknown"}
        />
        {schedule.next_run_at && (
          <Typography color="text.secondary" variant="caption">
            {formatDate(schedule.next_run_at)}
          </Typography>
        )}
      </Box>
      <Box>
        <Button
          color="error"
          onClick={() => onDelete(schedule)}
          size="small"
          startIcon={<Trash2 aria-hidden="true" size={14} />}
          variant="outlined"
        >
          Sil
        </Button>
      </Box>
    </Box>
  );
}

function ScheduleCreateDialog({
  open,
  onClose,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (request: ReportScheduleCreateRequest) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [reportType, setReportType] = useState("SUMMARY");
  const [format, setFormat] = useState("PDF");
  const [scheduleType, setScheduleType] = useState("DAILY");
  const [timezoneName, setTimezoneName] = useState("Europe/Istanbul");
  const [localTime, setLocalTime] = useState("08:00");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onSubmit({
        name,
        report_type: reportType,
        format,
        schedule_type: scheduleType,
        timezone_name: timezoneName,
        parameters: {},
        sensitivity_level: null,
        recipients: [],
        local_time: localTime || null,
        once_at: null,
        day_of_week: null,
        day_of_month: null,
      });
      onClose();
      setName("");
      setReportType("SUMMARY");
      setFormat("PDF");
      setScheduleType("DAILY");
      setTimezoneName("Europe/Istanbul");
      setLocalTime("08:00");
    } catch {
      // Error handled by parent
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      aria-describedby="schedule-create-dialog-description"
      aria-labelledby="schedule-create-dialog-title"
      maxWidth="sm"
      onClose={onClose}
      open={open}
      fullWidth
    >
      <DialogTitle id="schedule-create-dialog-title">Zamanlanmış Rapor Oluştur</DialogTitle>
      <DialogContent id="schedule-create-dialog-description">
        <Box sx={{ display: "grid", gap: 3, pt: 2 }}>
          <TextField
            label="Rapor adı"
            onChange={(e) => setName(e.target.value)}
            required
            value={name}
            fullWidth
          />
          <FormControl fullWidth>
            <InputLabel id="sched-report-type-label">Rapor türü</InputLabel>
            <Select
              label="Rapor türü"
              labelId="sched-report-type-label"
              onChange={(e) => setReportType(e.target.value)}
              value={reportType}
            >
              <MenuItem value="SUMMARY">Özet Rapor</MenuItem>
              <MenuItem value="DETAIL">Detay Rapor</MenuItem>
              <MenuItem value="TREND">Trend Raporu</MenuItem>
              <MenuItem value="CRITICAL_DATA">Kritik Veri Raporu</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel id="sched-format-label">Format</InputLabel>
            <Select
              label="Format"
              labelId="sched-format-label"
              onChange={(e) => setFormat(e.target.value)}
              value={format}
            >
              <MenuItem value="PDF">PDF</MenuItem>
              <MenuItem value="XLSX">Excel (XLSX)</MenuItem>
              <MenuItem value="CSV">CSV</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel id="sched-type-label">Sıklık</InputLabel>
            <Select
              label="Sıklık"
              labelId="sched-type-label"
              onChange={(e) => setScheduleType(e.target.value)}
              value={scheduleType}
            >
              <MenuItem value="DAILY">Günlük</MenuItem>
              <MenuItem value="WEEKLY">Haftalık</MenuItem>
              <MenuItem value="MONTHLY">Aylık</MenuItem>
              <MenuItem value="ONCE">Tek seferlik</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Zaman dilimi"
            onChange={(e) => setTimezoneName(e.target.value)}
            placeholder="Europe/Istanbul"
            value={timezoneName}
            fullWidth
          />
          <TextField
            label="Yerel saat (HH:MM)"
            onChange={(e) => setLocalTime(e.target.value)}
            placeholder="08:00"
            value={localTime}
            fullWidth
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button disabled={submitting} onClick={onClose}>İptal</Button>
        <Button
          disabled={submitting || !name.trim()}
          onClick={handleSubmit}
          variant="contained"
        >
          {submitting ? "Oluşturuluyor..." : "Oluştur"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function ScheduleDeleteDialog({
  open,
  onClose,
  onConfirm,
  scheduleName,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
  scheduleName: string;
}) {
  const [submitting, setSubmitting] = useState(false);

  const handleConfirm = async () => {
    setSubmitting(true);
    try {
      await onConfirm();
      onClose();
    } catch {
      // Error handled by parent
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      aria-describedby="schedule-delete-dialog-description"
      aria-labelledby="schedule-delete-dialog-title"
      maxWidth="xs"
      onClose={onClose}
      open={open}
    >
      <DialogTitle id="schedule-delete-dialog-title">Zamanlanmış Raporu Sil</DialogTitle>
      <DialogContent id="schedule-delete-dialog-description">
        <Typography>
          <strong>{scheduleName}</strong> zamanlanmış raporunu silmek istediğinize emin misiniz?
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button disabled={submitting} onClick={onClose}>İptal</Button>
        <Button
          color="error"
          disabled={submitting}
          onClick={handleConfirm}
          variant="contained"
        >
          {submitting ? "Siliniyor..." : "Sil"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export function ReportsPage({
  state = "normal",
  summary = syntheticReportSummary,
  reportItems = [],
  scheduleItems = syntheticSchedules,
  correlationId,
  onRefresh,
  onCreateReport,
  onDownloadReport,
  onCreateSchedule,
  onDeleteSchedule,
}: ReportsPageProps) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [level, setLevel] = useState("ALL");
  const [tabValue, setTabValue] = useState(0);
  const [requestDialogOpen, setRequestDialogOpen] = useState(false);
  const [scheduleCreateOpen, setScheduleCreateOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ReportSchedule | null>(null);

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

  const handleCreateReport = async (request: ReportRequest) => {
    if (onCreateReport) {
      await onCreateReport(request);
    }
  };

  const handleDownload = (reportId: string, filename: string) => {
    if (onDownloadReport) {
      void onDownloadReport(reportId, filename);
    }
  };

  const handleCreateSchedule = async (request: ReportScheduleCreateRequest) => {
    if (onCreateSchedule) {
      await onCreateSchedule(request);
    }
  };

  const handleDeleteSchedule = async (scheduleId: string) => {
    if (onDeleteSchedule) {
      await onDeleteSchedule(scheduleId);
    }
    setDeleteTarget(null);
  };

  const activeSchedules = scheduleItems.filter((s) => s.is_active);
  const inactiveSchedules = scheduleItems.filter((s) => !s.is_active);

  return (
    <AppShell currentPage="Raporlar">
      <Box sx={(theme) => ({ display: "grid", gap: 5, margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 4, lg: 6 }, width: "100%" })}>
        <Box sx={{ alignItems: { md: "center" }, display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, justifyContent: "space-between" }}>
          <Box>
            <Typography component="h1" variant="h1">Raporlar</Typography>
            <Typography color="text.secondary">Yetkili kaynaklarınızdaki toplulaştırılmış raporlar ve geçmiş talepler</Typography>
          </Box>
          {state !== "unauthorized" ? (
            <Box sx={{ display: "flex", gap: 2 }}>
              <Button onClick={() => setRequestDialogOpen(true)} startIcon={<FileDown aria-hidden="true" size={16} />} variant="contained">Rapor Talep Et</Button>
              <Button onClick={onRefresh} startIcon={<RefreshCw aria-hidden="true" size={16} />} variant="outlined">Yenile</Button>
            </Box>
          ) : null}
        </Box>

        {state !== "unauthorized" ? (
          <>
            <Tabs onChange={(_, v) => setTabValue(v)} value={tabValue}>
              <Tab label="Özet Görünüm" />
              <Tab label={`Rapor Geçmişi (${reportItems.length})`} />
              <Tab label={`Zamanlanmış (${scheduleItems.length})`} />
            </Tabs>

            {tabValue === 0 && (
              <>
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

                {state === "loading" ? <Box aria-busy="true" aria-label="Rapor önizlemesi yükleniyor">{Array.from({ length: 6 }, (_, index) => <Skeleton height={88} key={index} />)}</Box> : null}
                {state === "empty" || state === "error" ? <StateMessage correlationId={correlationId} onRefresh={onRefresh} state={state} /> : null}

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
              </>
            )}

            {tabValue === 1 && (
              <Paper component="section" sx={{ borderRadius: 1.5, overflow: "hidden" }} variant="outlined">
                <Box sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
                  <Typography component="h2" variant="h3">Rapor Geçmişi</Typography>
                  <Typography color="text.secondary" variant="body2">{reportItems.length} rapor</Typography>
                </Box>
                {reportItems.length === 0 ? (
                  <Box sx={{ px: 4, py: 6 }}>
                    <Typography color="text.secondary" sx={{ textAlign: "center" }}>Henüz rapor talebiniz bulunmuyor.</Typography>
                  </Box>
                ) : (
                  <>
                    <Box aria-hidden="true" sx={{ borderBottom: 1, borderColor: "divider", color: "text.secondary", display: { xs: "none", md: "grid" }, fontSize: "caption.fontSize", fontWeight: 700, gap: 3, gridTemplateColumns: "40px minmax(180px, 1fr) minmax(100px, .4fr) minmax(120px, .5fr) auto", px: 4, py: 2 }}>
                      <Box /><Box>Rapor</Box><Box>Format</Box><Box>Durum</Box><Box />
                    </Box>
                    <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
                      {reportItems.map((item) => (
                        <ReportHistoryRow key={item.report_id} item={item} onDownload={handleDownload} />
                      ))}
                    </Box>
                  </>
                )}
              </Paper>
            )}

            {tabValue === 2 && (
              <Paper component="section" sx={{ borderRadius: 1.5, overflow: "hidden" }} variant="outlined">
                <Box sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
                  <Typography component="h2" variant="h3">Zamanlanmış Raporlar</Typography>
                  <Box sx={{ display: "flex", gap: 2 }}>
                    <Typography color="text.secondary" variant="body2">{scheduleItems.length} zamanlama</Typography>
                    <Button
                      onClick={() => setScheduleCreateOpen(true)}
                      size="small"
                      startIcon={<Plus aria-hidden="true" size={14} />}
                      variant="contained"
                    >
                      Yeni Zamanlama
                    </Button>
                  </Box>
                </Box>
                {scheduleItems.length === 0 ? (
                  <Box sx={{ px: 4, py: 6 }}>
                    <Typography color="text.secondary" sx={{ textAlign: "center" }}>Henüz zamanlanmış rapor bulunmuyor.</Typography>
                  </Box>
                ) : (
                  <>
                    <Box aria-hidden="true" sx={{ borderBottom: 1, borderColor: "divider", color: "text.secondary", display: { xs: "none", md: "grid" }, fontSize: "caption.fontSize", fontWeight: 700, gap: 3, gridTemplateColumns: "40px minmax(180px, 1fr) minmax(100px, .4fr) minmax(100px, .4fr) minmax(140px, .5fr) auto", px: 4, py: 2 }}>
                      <Box /><Box>Zamanlama</Box><Box>Format</Box><Box>Sıklık</Box><Box>Durum</Box><Box />
                    </Box>
                    <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
                      {activeSchedules.map((s) => (
                        <ScheduleRow key={s.schedule_id} schedule={s} onDelete={setDeleteTarget} />
                      ))}
                      {inactiveSchedules.map((s) => (
                        <ScheduleRow key={s.schedule_id} schedule={s} onDelete={setDeleteTarget} />
                      ))}
                    </Box>
                  </>
                )}
              </Paper>
            )}
          </>
        ) : (
          <StateMessage correlationId={correlationId} onRefresh={onRefresh} state="unauthorized" />
        )}
      </Box>

      <ReportRequestDialog
        onClose={() => setRequestDialogOpen(false)}
        onSubmit={handleCreateReport}
        open={requestDialogOpen}
      />
      <ScheduleCreateDialog
        onClose={() => setScheduleCreateOpen(false)}
        onSubmit={handleCreateSchedule}
        open={scheduleCreateOpen}
      />
      {deleteTarget && (
        <ScheduleDeleteDialog
          onClose={() => setDeleteTarget(null)}
          onConfirm={() => handleDeleteSchedule(deleteTarget.schedule_id)}
          open={true}
          scheduleName={deleteTarget.name}
        />
      )}
    </AppShell>
  );
}