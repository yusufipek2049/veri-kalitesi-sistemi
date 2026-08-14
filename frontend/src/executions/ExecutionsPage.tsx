import { useMemo, useState } from "react";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import {
  Braces,
  Ban,
  CheckCircle2,
  CircleDashed,
  Clock3,
  Code2,
  Database,
  Lock,
  PlayCircle,
  RefreshCw,
  Search,
  Server,
  TimerOff,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens, type StatusTone } from "../theme/tokens";
import {
  syntheticExecutions,
  type ExecutionDetail,
  type ExecutionDatasetRef,
  type ExecutionListItem,
  type ExecutionState,
  type JobInfo,
} from "./model";

export interface ExecutionRuleOption {
  ruleVersionId: string;
  label: string;
}

export interface ExecutionSourceOption {
  sourceId: string;
  label: string;
}

interface ExecutionsPageProps {
  state?: ExecutionState;
  items?: ExecutionListItem[];
  correlationId?: string;
  onRefresh?: () => void;
  onStart?: (ruleVersionIds: string[], sourceIds: string[], idempotencyKey: string) => void;
  onCancel?: (executionId: string, reason: string) => void;
  onAdhocSql?: (sql: string, sourceIds: string[], timeoutSeconds: number, rowLimit: number) => Promise<void>;
  onSelect?: (executionId: string) => void;
  starting?: boolean;
  cancelling?: boolean;
  adhocSqlLoading?: boolean;
  executionDetail?: ExecutionDetail | null;
  detailOpen?: boolean;
  detailLoading?: boolean;
  onCloseDetail?: () => void;
  ruleOptions?: ExecutionRuleOption[];
  sourceOptions?: ExecutionSourceOption[];
  datasetFilterOptions?: Array<{ value: string; label: string }>;
  scheduleFilterOptions?: Array<{ value: string; label: string }>;
  activeDatasetFilter?: string;
  activeScheduleFilter?: string;
  onFilterChange?: (filters: { datasetId?: string; scheduleId?: string }) => void;
}

const statusLabels: Record<string, string> = {
  QUEUED: "Kuyrukta",
  RUNNING: "Çalışıyor",
  BLOCKED: "Engellenmiş",
  CANCEL_REQUESTED: "İptal bekliyor",
  SUCCESS: "Tamamlandı",
  PARTIAL: "Kısmi",
  TECHNICAL_ERROR: "Teknik hata",
  TIMEOUT: "Zaman aşımı",
  CANCELLED: "İptal edildi",
};

const typeLabels: Record<string, string> = {
  MANUAL: "Manuel",
  SCHEDULED: "Zamanlanmış",
};

const errorLabels: Record<string, string> = {
  CONNECTION_UNAVAILABLE: "Bağlantı kullanılamıyor",
  QUERY_TIMEOUT: "Sorgu zaman aşımı",
  TOTAL_TIMEOUT: "Toplam süre aşıldı",
};

function executionPresentation(status: string): { icon: LucideIcon; tone: StatusTone } {
  if (status === "SUCCESS") return { icon: CheckCircle2, tone: "success" };
  if (status === "RUNNING") return { icon: PlayCircle, tone: "info" };
  if (status === "BLOCKED") return { icon: Lock, tone: "warning" };
  if (status === "PARTIAL") return { icon: CircleDashed, tone: "warning" };
  if (status === "TECHNICAL_ERROR") return { icon: Wrench, tone: "technical" };
  if (status === "TIMEOUT") return { icon: TimerOff, tone: "technical" };
  if (status === "CANCEL_REQUESTED") return { icon: Ban, tone: "warning" };
  if (status === "CANCELLED") return { icon: Ban, tone: "unknown" };
  return { icon: Clock3, tone: "unknown" };
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function durationLabel(item: ExecutionListItem): string {
  if (!item.startedAt) return "Henüz başlamadı";
  if (!item.finishedAt) return "Devam ediyor";
  const seconds = Math.max(
    0,
    Math.round((new Date(item.finishedAt).getTime() - new Date(item.startedAt).getTime()) / 1000),
  );
  if (seconds >= 3600) return `${Math.floor(seconds / 3600)} sa ${Math.round((seconds % 3600) / 60)} dk`;
  if (seconds >= 60) return `${Math.floor(seconds / 60)} dk`;
  return `${seconds} sn`;
}

function datasetLabel(ds: ExecutionDatasetRef): string {
  if (ds.name && ds.namespace) return `${ds.name} (${ds.namespace})`;
  if (ds.name) return ds.name;
  return ds.sourceName || ds.sourceId;
}

function ExecutionRow({
  item,
  onCancel,
  onSelect,
  cancelling,
}: {
  item: ExecutionListItem;
  onCancel?: (id: string) => void;
  onSelect?: (id: string) => void;
  cancelling?: boolean;
}) {
  const presentation = executionPresentation(item.status);
  const Icon = presentation.icon;
  const canCancel = item.availableActions.includes("cancel");
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
          md: "40px minmax(230px, 1fr) minmax(145px, .65fr) minmax(150px, .65fr)",
          lg: "40px minmax(240px, 1.2fr) minmax(145px, .65fr) minmax(130px, .55fr) minmax(155px, .7fr) minmax(180px, .8fr) minmax(100px, auto)",
        },
        minHeight: 84,
        px: 4,
        py: 3,
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Box
        aria-hidden="true"
        data-testid="execution-icon-slot"
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
        <Typography
          noWrap
          sx={{ cursor: onSelect ? "pointer" : undefined, fontWeight: 700 }}
          onClick={() => onSelect?.(item.id)}
        >
          {item.id}
        </Typography>
        <Typography color="text.secondary" variant="caption">
          {typeLabels[item.executionType] ?? item.executionType} · {item.ruleCount} kural · {item.sourceCount} kaynak
        </Typography>
        {item.datasets.length > 0 ? (
          <Box sx={{ alignItems: "center", display: "flex", flexWrap: "wrap", gap: 0.5, mt: 0.5 }}>
            <Database aria-hidden="true" size={12} style={{ opacity: 0.6 }} />
            {item.datasets.map((ds, index) => (
              <Typography key={`${ds.sourceId}-${ds.datasetId}-${index}`} color="text.secondary" variant="caption">
                {index > 0 ? " · " : ""}{datasetLabel(ds)}{ds.sourceName ? ` @ ${ds.sourceName}` : ""}
              </Typography>
            ))}
          </Box>
        ) : null}
        {item.scheduleId ? (
          <Typography color="info.main" variant="caption">
            Zamanlanmış: {item.scheduleId}
          </Typography>
        ) : null}
        {item.blockedReasonCode ? (
          <Typography color="warning.main" variant="caption">
            Engellendi: {item.blockedReasonCode}
          </Typography>
        ) : null}
        {(item.status === "RUNNING" || item.status === "QUEUED") && item.progressPercent > 0 ? (
          <Box sx={{ alignItems: "center", display: "flex", gap: 1, mt: 0.5 }}>
            <LinearProgress
              aria-label={`İlerleme: %${item.progressPercent}`}
              sx={{ flexGrow: 1, height: 6, borderRadius: 1 }}
              value={item.progressPercent}
              variant="determinate"
            />
            <Typography color="text.secondary" variant="caption">%{item.progressPercent}</Typography>
          </Box>
        ) : null}
      </Box>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" } }}>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          <StatusBadge
            label={statusLabels[item.status] ?? item.status}
            tone={presentation.tone}
          />
          {item.executionMode === "SHADOW" ? (
            <StatusBadge label="SHADOW" tone="warning" />
          ) : null}
        </Box>
      </Box>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" } }}>
        <Typography variant="body2">{item.workloadClass === "HEAVY" ? "Yoğun iş" : "Hafif iş"}</Typography>
        <Typography color="text.secondary" variant="caption">{item.attemptCount} deneme</Typography>
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" } }}>
        <Typography variant="body2">{formatDate(item.createdAt)}</Typography>
        <Typography color="text.secondary" variant="caption">{durationLabel(item)}</Typography>
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" }, minWidth: 0 }}>
        <Typography noWrap variant="body2">
          {item.errorClass ? errorLabels[item.errorClass] ?? item.errorClass : "Teknik hata yok"}
        </Typography>
        <Typography color="text.secondary" variant="caption">
          {item.finishedAt ? `Bitiş: ${formatDate(item.finishedAt)}` : "Henüz kapanmadı"}
        </Typography>
      </Box>
      <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
        {canCancel && onCancel ? (
          <Button
            color="warning"
            disabled={cancelling}
            onClick={() => onCancel(item.id)}
            size="small"
            startIcon={<Ban aria-hidden="true" size={14} />}
            variant="outlined"
          >
            İptal
          </Button>
        ) : null}
      </Box>
    </Box>
  );
}

function StateMessage({
  state,
  correlationId,
  onRefresh,
}: Pick<ExecutionsPageProps, "correlationId" | "onRefresh"> & {
  state: "empty" | "error" | "unauthorized";
}) {
  const content = {
    empty: ["Çalıştırma bulunamadı", "Yetkili kapsam ve seçili filtrelerle eşleşen çalıştırma yok."],
    error: ["Çalıştırmalar yüklenemedi", `Teknik bir sorun oluştu. Yeniden deneyin. İzleme kodu: ${correlationId ?? "bulunamadı"}.`],
    unauthorized: ["Bu görünüm için yetkiniz yok", "Çalıştırma geçmişi gösterilmedi. Erişim talebi için yetkili biriminizle iletişime geçin."],
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

const jobStatusLabels: Record<string, string> = {
  QUEUED: "Kuyrukta",
  LEASED: "Kiralanmış",
  RUNNING: "Çalışıyor",
  SUCCESS: "Tamamlandı",
  TECHNICAL_ERROR: "Teknik hata",
  TIMEOUT: "Zaman aşımı",
  CANCELLED: "İptal edildi",
  CANCEL_REQUESTED: "İptal bekliyor",
  BLOCKED: "Engellenmiş",
};

function JobInfoSection({ jobInfo }: { jobInfo: JobInfo }) {
  return (
    <Box>
      <Typography sx={{ alignItems: "center", display: "flex", fontWeight: 700, gap: 1, mb: 1 }} variant="subtitle1">
        <Server aria-hidden="true" size={18} />
        Job Bilgileri
      </Typography>
      <Box sx={{ display: "grid", gap: 0.5 }}>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Typography color="text.secondary" sx={{ minWidth: 140 }} variant="body2">Job ID</Typography>
          <Typography sx={{ fontFamily: "monospace", fontSize: "0.85rem" }} variant="body2">{jobInfo.jobId}</Typography>
        </Box>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Typography color="text.secondary" sx={{ minWidth: 140 }} variant="body2">Durum</Typography>
          <StatusBadge
            label={jobStatusLabels[jobInfo.status] ?? jobInfo.status}
            tone={jobInfo.status === "SUCCESS" ? "success" : jobInfo.status === "RUNNING" ? "info" : jobInfo.status === "TECHNICAL_ERROR" || jobInfo.status === "TIMEOUT" ? "critical" : "unknown"}
          />
        </Box>
        {jobInfo.workerId ? (
          <Box sx={{ display: "flex", gap: 1 }}>
            <Typography color="text.secondary" sx={{ minWidth: 140 }} variant="body2">Worker</Typography>
            <Typography sx={{ fontFamily: "monospace", fontSize: "0.85rem" }} variant="body2">{jobInfo.workerId}</Typography>
          </Box>
        ) : null}
        {jobInfo.queuePosition != null ? (
          <Box sx={{ display: "flex", gap: 1 }}>
            <Typography color="text.secondary" sx={{ minWidth: 140 }} variant="body2">Kuyruk sırası</Typography>
            <Typography variant="body2">{jobInfo.queuePosition}</Typography>
          </Box>
        ) : null}
        <Box sx={{ display: "flex", gap: 1 }}>
          <Typography color="text.secondary" sx={{ minWidth: 140 }} variant="body2">Deneme sayısı</Typography>
          <Typography variant="body2">{jobInfo.attemptCount}</Typography>
        </Box>
        {jobInfo.leasedUntil ? (
          <Box sx={{ display: "flex", gap: 1 }}>
            <Typography color="text.secondary" sx={{ minWidth: 140 }} variant="body2">Lease bitiş</Typography>
            <Typography variant="body2">{formatDate(jobInfo.leasedUntil)}</Typography>
          </Box>
        ) : null}
        {jobInfo.lastErrorClass ? (
          <Box sx={{ display: "flex", gap: 1 }}>
            <Typography color="text.secondary" sx={{ minWidth: 140 }} variant="body2">Son hata</Typography>
            <Typography variant="body2">{errorLabels[jobInfo.lastErrorClass] ?? jobInfo.lastErrorClass}</Typography>
          </Box>
        ) : null}
        {jobInfo.completedAt ? (
          <Box sx={{ display: "flex", gap: 1 }}>
            <Typography color="text.secondary" sx={{ minWidth: 140 }} variant="body2">Tamamlanma</Typography>
            <Typography variant="body2">{formatDate(jobInfo.completedAt)}</Typography>
          </Box>
        ) : null}
        {jobInfo.completionOutcome ? (
          <Box sx={{ display: "flex", gap: 1 }}>
            <Typography color="text.secondary" sx={{ minWidth: 140 }} variant="body2">Sonuç</Typography>
            <Typography variant="body2">{jobInfo.completionOutcome}</Typography>
          </Box>
        ) : null}
      </Box>
    </Box>
  );
}

export function ExecutionsPage({
  state = "normal",
  items = syntheticExecutions,
  correlationId,
  onRefresh,
  onStart,
  onCancel,
  onSelect,
  starting,
  cancelling,
  adhocSqlLoading,
  onAdhocSql,
  executionDetail,
  detailOpen = false,
  detailLoading = false,
  onCloseDetail,
  ruleOptions = [],
  sourceOptions = [],
  datasetFilterOptions = [],
  scheduleFilterOptions = [],
  activeDatasetFilter,
  activeScheduleFilter,
  onFilterChange,
}: ExecutionsPageProps) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [executionType, setExecutionType] = useState("ALL");
  const [period, setPeriod] = useState("ALL");
  const [startDialogOpen, setStartDialogOpen] = useState(false);
  const [cancelTarget, setCancelTarget] = useState<string | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [selectedRule, setSelectedRule] = useState<ExecutionRuleOption | null>(null);
  const [selectedSource, setSelectedSource] = useState<ExecutionSourceOption | null>(null);
  const [startIdempotencyKey, setStartIdempotencyKey] = useState("");
  const [adhocDialogOpen, setAdhocDialogOpen] = useState(false);
  const [adhocSql, setAdhocSql] = useState("");
  const [adhocSqlError, setAdhocSqlError] = useState<string | null>(null);
  const [adhocSource, setAdhocSource] = useState<ExecutionSourceOption | null>(null);
  const [adhocTimeout, setAdhocTimeout] = useState(30);
  const [adhocRowLimit, setAdhocRowLimit] = useState(1000);

  const newestTime = Math.max(...items.map((item) => new Date(item.createdAt).getTime()));
  const visibleItems = useMemo(
    () => items.filter((item) => {
      const ageDays = (newestTime - new Date(item.createdAt).getTime()) / 86_400_000;
      return item.id.toLocaleLowerCase("tr-TR").includes(query.toLocaleLowerCase("tr-TR"))
        && (status === "ALL" || item.status === status)
        && (executionType === "ALL" || item.executionType === executionType)
        && (period === "ALL" || (period === "LATEST_DAY" ? ageDays < 1 : ageDays <= 7));
    }),
    [executionType, items, newestTime, period, query, status],
  );
  const effectiveItems = state === "long-content"
    ? Array.from({ length: 4 }, (_, group) => items.map((item) => ({
      ...item,
      id: `${item.id}-${group + 1}`,
    }))).flat()
    : visibleItems;

  const openStartDialog = () => {
    setStartIdempotencyKey(crypto.randomUUID());
    setSelectedRule(null);
    setSelectedSource(null);
    setStartDialogOpen(true);
  };

  const openAdhocDialog = () => {
    setAdhocSql("");
    setAdhocSqlError(null);
    setAdhocSource(null);
    setAdhocTimeout(30);
    setAdhocRowLimit(1000);
    setAdhocDialogOpen(true);
  };

  const validateAdhocSql = (sql: string): string | null => {
    const trimmed = sql.trim();
    if (!trimmed) return "SQL sorgusu zorunludur.";
    const upper = trimmed.toUpperCase();
    if (!upper.startsWith("SELECT")) return "SQL sorgusu SELECT ile başlamalıdır.";
    const forbidden = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE", "CREATE"];
    for (const keyword of forbidden) {
      if (upper.includes(`${keyword} `)) return `SQL sorgusu ${keyword} içermemelidir.`;
    }
    return null;
  };

  const handleAdhocSubmit = async () => {
    const err = validateAdhocSql(adhocSql);
    if (err) { setAdhocSqlError(err); return; }
    if (!onAdhocSql) return;
    setAdhocSqlError(null);
    try {
      await onAdhocSql(adhocSql.trim(), adhocSource ? [adhocSource.sourceId] : [], adhocTimeout, adhocRowLimit);
      setAdhocDialogOpen(false);
    } catch {
      setAdhocSqlError("Çalıştırma başlatılamadı. Lütfen bilgileri kontrol edin.");
    }
  };

  const handleStartSubmit = () => {
    if (!selectedRule || !startIdempotencyKey) return;
    onStart?.(
      [selectedRule.ruleVersionId],
      selectedSource ? [selectedSource.sourceId] : [],
      startIdempotencyKey,
    );
    setStartDialogOpen(false);
    setSelectedRule(null);
    setSelectedSource(null);
    setStartIdempotencyKey("");
  };

  const handleCancelConfirm = () => {
    if (!cancelTarget || !cancelReason.trim()) return;
    onCancel?.(cancelTarget, cancelReason.trim());
    setCancelTarget(null);
    setCancelReason("");
  };

  return (
    <AppShell currentPage="Çalıştırmalar">
      <Box sx={(theme) => ({ display: "grid", gap: 5, margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 4, lg: 6 }, width: "100%" })}>
        <Box sx={{ alignItems: { md: "center" }, display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, justifyContent: "space-between" }}>
          <Box>
            <Typography component="h1" variant="h1">Çalıştırmalar</Typography>
            <Typography color="text.secondary">Yetkili kaynak kapsamınızdaki salt okunur çalışma geçmişi</Typography>
          </Box>
          <Box sx={{ display: "flex", gap: 2 }}>
            {onStart ? (
              <Button onClick={openStartDialog} startIcon={<PlayCircle aria-hidden="true" size={16} />} variant="contained">
                Çalıştırma başlat
              </Button>
            ) : null}
            {onAdhocSql ? (
              <Button onClick={openAdhocDialog} startIcon={<Braces aria-hidden="true" size={16} />} variant="outlined">
                Özel SQL
              </Button>
            ) : null}
            {state !== "unauthorized" ? <Button onClick={onRefresh} startIcon={<RefreshCw aria-hidden="true" size={16} />} variant="contained">Yenile</Button> : null}
          </Box>
        </Box>

        {state !== "unauthorized" ? (
          <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
            <Box aria-label="Çalıştırma filtreleri" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(180px, 1fr))", lg: "minmax(240px, 1.4fr) repeat(4, minmax(145px, .7fr))" } }}>
              <TextField label="Çalıştırma ara" onChange={(event) => setQuery(event.target.value)} slotProps={{ input: { startAdornment: <Search aria-hidden="true" size={16} /> } }} value={query} />
              <FormControl><InputLabel id="execution-status-label">Durum</InputLabel><Select label="Durum" labelId="execution-status-label" onChange={(event) => setStatus(event.target.value)} value={status}><MenuItem value="ALL">Tüm durumlar</MenuItem>{Object.entries(statusLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <FormControl><InputLabel id="execution-type-label">Tür</InputLabel><Select label="Tür" labelId="execution-type-label" onChange={(event) => setExecutionType(event.target.value)} value={executionType}><MenuItem value="ALL">Tüm türler</MenuItem>{Object.entries(typeLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <FormControl><InputLabel id="execution-period-label">Tarih</InputLabel><Select label="Tarih" labelId="execution-period-label" onChange={(event) => setPeriod(event.target.value)} value={period}><MenuItem value="ALL">Tüm tarihler</MenuItem><MenuItem value="LATEST_DAY">Son kayıt günü</MenuItem><MenuItem value="LAST_7_DAYS">Son 7 gün</MenuItem></Select></FormControl>
              <FormControl><InputLabel id="execution-scope-label">Kapsam</InputLabel><Select disabled label="Kapsam" labelId="execution-scope-label" value="AUTHORIZED"><MenuItem value="AUTHORIZED">Yetkili kaynaklar</MenuItem></Select></FormControl>
            </Box>
            {(datasetFilterOptions.length > 0 || scheduleFilterOptions.length > 0) ? (
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2, mt: 2 }}>
                {datasetFilterOptions.length > 0 ? (
                  <FormControl size="small" sx={{ minWidth: 180 }}>
                    <InputLabel id="execution-dataset-filter-label">Tablo</InputLabel>
                    <Select
                      label="Tablo"
                      labelId="execution-dataset-filter-label"
                      onChange={(event) => onFilterChange?.({ datasetId: event.target.value || undefined, scheduleId: activeScheduleFilter })}
                      value={activeDatasetFilter ?? ""}
                    >
                      <MenuItem value="">Tüm tablolar</MenuItem>
                      {datasetFilterOptions.map((opt) => <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>)}
                    </Select>
                  </FormControl>
                ) : null}
                {scheduleFilterOptions.length > 0 ? (
                  <FormControl size="small" sx={{ minWidth: 180 }}>
                    <InputLabel id="execution-schedule-filter-label">Schedule</InputLabel>
                    <Select
                      label="Schedule"
                      labelId="execution-schedule-filter-label"
                      onChange={(event) => onFilterChange?.({ datasetId: activeDatasetFilter, scheduleId: event.target.value || undefined })}
                      value={activeScheduleFilter ?? ""}
                    >
                      <MenuItem value="">Tüm schedule'lar</MenuItem>
                      {scheduleFilterOptions.map((opt) => <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>)}
                    </Select>
                  </FormControl>
                ) : null}
              </Box>
            ) : null}
          </Paper>
        ) : null}

        {state === "loading" ? <Box aria-busy="true" aria-label="Çalıştırmalar yükleniyor">{Array.from({ length: 6 }, (_, index) => <Skeleton height={84} key={index} />)}</Box> : null}
        {state === "empty" || state === "error" || state === "unauthorized" ? <StateMessage correlationId={correlationId} onRefresh={onRefresh} state={state} /> : null}
        {(state === "normal" || state === "long-content") && effectiveItems.length === 0 ? <StateMessage state="empty" /> : null}
        {(state === "normal" || state === "long-content") && effectiveItems.length > 0 ? (
          <Paper component="section" sx={{ borderRadius: 1.5, overflow: "hidden" }} variant="outlined">
            <Box sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
              <Typography component="h2" variant="h3">Çalıştırma Geçmişi</Typography>
              <Typography color="text.secondary" variant="body2">{effectiveItems.length} kayıt · en fazla 100</Typography>
            </Box>
            <Box
              aria-hidden="true"
              sx={{
                borderBottom: 1,
                borderColor: "divider",
                color: "text.secondary",
                display: { xs: "none", lg: "grid" },
                fontSize: "caption.fontSize",
                fontWeight: 700,
                gap: 3,
                gridTemplateColumns: "40px minmax(240px, 1.2fr) minmax(145px, .65fr) minmax(130px, .55fr) minmax(155px, .7fr) minmax(180px, .8fr) minmax(100px, auto)",
                px: 4,
                py: 2,
              }}
            >
              <Box />
              <Box>Çalıştırma</Box>
              <Box>Durum</Box>
              <Box>İş yükü</Box>
              <Box>Zaman</Box>
              <Box>Teknik sonuç</Box>
              <Box />
            </Box>
            <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
              {effectiveItems.map((item) => (
                <ExecutionRow
                  cancelling={cancelling}
                  item={item}
                  key={item.id}
                  onCancel={onCancel ? (id) => setCancelTarget(id) : undefined}
                  onSelect={onSelect}
                />
              ))}
            </Box>
          </Paper>
        ) : null}
      </Box>

      <Dialog fullWidth maxWidth="sm" onClose={() => setStartDialogOpen(false)} open={startDialogOpen}>
        <DialogTitle>Çalıştırma başlat</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 2 }}>
          <Autocomplete
            fullWidth
            getOptionLabel={(option) => option.label}
            isOptionEqualToValue={(option, value) => option.ruleVersionId === value.ruleVersionId}
            noOptionsText={ruleOptions.length === 0 ? "Kural bulunamadı" : undefined}
            onChange={(_, value) => setSelectedRule(value)}
            options={ruleOptions}
            renderInput={(params) => <TextField {...params} label="Kural" required />}
            value={selectedRule}
          />
          <Autocomplete
            fullWidth
            getOptionLabel={(option) => option.label}
            isOptionEqualToValue={(option, value) => option.sourceId === value.sourceId}
            noOptionsText={sourceOptions.length === 0 ? "Kaynak bulunamadı" : undefined}
            onChange={(_, value) => setSelectedSource(value)}
            options={sourceOptions}
            renderInput={(params) => <TextField {...params} label="Kaynak (isteğe bağlı)" />}
            value={selectedSource}
          />
          <TextField
            fullWidth
            label="Idempotency anahtarı"
            onChange={(e) => setStartIdempotencyKey(e.target.value)}
            required
            value={startIdempotencyKey}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setStartDialogOpen(false)}>Vazgeç</Button>
          <Button disabled={starting || !selectedRule || !startIdempotencyKey} onClick={handleStartSubmit} variant="contained">
            Başlat
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog fullWidth maxWidth="md" onClose={() => { if (!adhocSqlLoading) setAdhocDialogOpen(false); }} open={adhocDialogOpen}>
        <DialogTitle>Özel SQL Çalıştır</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 2 }}>
          <Typography color="text.secondary" variant="body2">
            Salt okunur bir SQL sorgusu yazın. Sistem otomatik olarak bir CUSTOM_SQL kuralı oluşturur ve çalıştırma başlatır.
          </Typography>
          <TextField
            fullWidth
            label="SQL Sorgusu"
            multiline
            minRows={6}
            maxRows={16}
            onChange={(e) => { setAdhocSql(e.target.value); setAdhocSqlError(null); }}
            placeholder="SELECT ... -- Salt okunur SQL sorgusunu giriniz"
            required
            error={!!adhocSqlError}
            helperText={adhocSqlError ?? "SELECT ile başlamalı; DROP, DELETE, INSERT, UPDATE içermemelidir."}
            sx={{ "& .MuiInputBase-input": { fontFamily: "monospace", fontSize: 13 } }}
            value={adhocSql}
          />
          <Autocomplete
            fullWidth
            getOptionLabel={(option) => option.label}
            isOptionEqualToValue={(option, value) => option.sourceId === value.sourceId}
            noOptionsText={sourceOptions.length === 0 ? "Kaynak bulunamadı" : undefined}
            onChange={(_, value) => setAdhocSource(value)}
            options={sourceOptions}
            renderInput={(params) => <TextField {...params} label="Kaynak (isteğe bağlı)" />}
            value={adhocSource}
          />
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: "1fr 1fr" }}>
            <TextField
              fullWidth
              label="Zaman Aşımı (sn)"
              onChange={(e) => setAdhocTimeout(Number(e.target.value))}
              type="number"
              value={adhocTimeout}
            />
            <TextField
              fullWidth
              label="Satır Limiti"
              onChange={(e) => setAdhocRowLimit(Number(e.target.value))}
              type="number"
              value={adhocRowLimit}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button disabled={adhocSqlLoading} onClick={() => setAdhocDialogOpen(false)}>Vazgeç</Button>
          <Button disabled={adhocSqlLoading || !adhocSql.trim()} onClick={() => void handleAdhocSubmit()} variant="contained">
            {adhocSqlLoading ? "Çalıştırılıyor..." : "Çalıştır"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog fullWidth maxWidth="sm" onClose={() => setCancelTarget(null)} open={cancelTarget !== null}>
        <DialogTitle>Çalıştırmayı iptal et</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 2 }}>
          <Typography variant="body2">
            {cancelTarget} kimlikli çalıştırma iptal edilecek.
          </Typography>
          <TextField
            fullWidth
            label="İptal nedeni"
            minRows={2}
            multiline
            onChange={(e) => setCancelReason(e.target.value)}
            required
            value={cancelReason}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCancelTarget(null)}>Vazgeç</Button>
          <Button color="warning" disabled={cancelling || !cancelReason.trim()} onClick={handleCancelConfirm} variant="contained">
            İptal et
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog fullWidth maxWidth="md" onClose={onCloseDetail} open={detailOpen}>
        <DialogTitle>Çalıştırma detayı</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 3, pt: 2 }}>
          {detailLoading ? (
            <Box aria-busy="true">
              {Array.from({ length: 3 }, (_, i) => <Skeleton height={40} key={i} />)}
            </Box>
          ) : executionDetail ? (
            <>
              <Box sx={{ display: "grid", gap: 1 }}>
                <Typography sx={{ fontWeight: 700 }} variant="h6">
                  {executionDetail.item.id}
                </Typography>
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                  <StatusBadge
                    label={statusLabels[executionDetail.item.status] ?? executionDetail.item.status}
                    tone={executionPresentation(executionDetail.item.status).tone}
                  />
                  <Chip label={typeLabels[executionDetail.item.executionType] ?? executionDetail.item.executionType} size="small" variant="outlined" />
                  <Chip label={`${executionDetail.item.ruleCount} kural`} size="small" variant="outlined" />
                  <Chip label={`${executionDetail.item.sourceCount} kaynak`} size="small" variant="outlined" />
                </Box>
                {executionDetail.item.datasets.length > 0 ? (
                  <Box sx={{ alignItems: "center", display: "flex", flexWrap: "wrap", gap: 1 }}>
                    <Database aria-hidden="true" size={14} style={{ opacity: 0.6 }} />
                    {executionDetail.item.datasets.map((ds, index) => (
                      <Chip
                        key={`detail-ds-${ds.sourceId}-${ds.datasetId}-${index}`}
                        label={`${datasetLabel(ds)}${ds.sourceName ? ` @ ${ds.sourceName}` : ""}`}
                        size="small"
                        variant="outlined"
                        color="info"
                      />
                    ))}
                  </Box>
                ) : null}
                {executionDetail.item.scheduleId ? (
                  <Typography color="info.main" variant="caption">
                    Zamanlanmış: {executionDetail.item.scheduleId}
                  </Typography>
                ) : null}
                <Typography color="text.secondary" variant="caption">
                  Oluşturulma: {formatDate(executionDetail.item.createdAt)}
                  {executionDetail.item.startedAt ? ` · Başlangıç: ${formatDate(executionDetail.item.startedAt)}` : ""}
                  {executionDetail.item.finishedAt ? ` · Bitiş: ${formatDate(executionDetail.item.finishedAt)}` : ""}
                </Typography>
              </Box>

              <Divider />

              <Box>
                <Typography sx={{ fontWeight: 700, mb: 1 }} variant="subtitle1">
                  Sonuçlar
                </Typography>
                {executionDetail.results.length > 0 ? (
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Kural Sürümü</TableCell>
                        <TableCell align="right">Popülasyon</TableCell>
                        <TableCell align="right">Uyan</TableCell>
                        <TableCell align="right">Uyumsuz</TableCell>
                        <TableCell align="right">Değerlendirilen</TableCell>
                        <TableCell>Durum</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {executionDetail.results.map((r) => (
                        <TableRow key={r.ruleVersionId}>
                          <TableCell sx={{ fontFamily: "monospace", fontSize: "0.8rem" }}>
                            {r.ruleVersionId.slice(0, 8)}…
                          </TableCell>
                          <TableCell align="right">{r.populationCount ?? "—"}</TableCell>
                          <TableCell align="right">{r.passedCount ?? "—"}</TableCell>
                          <TableCell align="right">{r.failedCount ?? "—"}</TableCell>
                          <TableCell align="right">{r.evaluatedCount ?? "—"}</TableCell>
                          <TableCell>
                            <StatusBadge
                              label={r.measurementStatus ?? "—"}
                              tone={r.measurementStatus === "PASSED" ? "success" : r.measurementStatus === "FAILED" ? "critical" : "unknown"}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <Typography color="text.secondary" variant="body2">Sonuç bulunamadı.</Typography>
                )}
              </Box>

              {executionDetail.ruleDefinitions.length > 0 && (
                <>
                  <Divider />
                  <Box>
                    <Typography sx={{ alignItems: "center", display: "flex", fontWeight: 700, gap: 1, mb: 1 }} variant="subtitle1">
                      <Code2 aria-hidden="true" size={18} />
                      SQL Sorguları
                    </Typography>
                    {executionDetail.ruleDefinitions.map((def) => (
                      <Box key={def.ruleVersionId} sx={{ mb: 2 }}>
                        <Box sx={{ alignItems: "center", display: "flex", gap: 1, mb: 0.5 }}>
                          <Typography sx={{ fontFamily: "monospace", fontSize: "0.8rem" }}>
                            {def.ruleVersionId.slice(0, 8)}…
                          </Typography>
                          {def.ruleType && <Chip label={def.ruleType} size="small" variant="outlined" />}
                        </Box>
                        {def.sql ? (
                          <Box
                            component="pre"
                            sx={{
                              bgcolor: "grey.50",
                              border: 1,
                              borderColor: "divider",
                              borderRadius: 1,
                              fontFamily: "monospace",
                              fontSize: "0.8rem",
                              maxHeight: 300,
                              overflow: "auto",
                              p: 2,
                              whiteSpace: "pre-wrap",
                              wordBreak: "break-word",
                            }}
                          >
                            {def.sql}
                          </Box>
                        ) : (
                          <Typography color="text.secondary" variant="body2">
                            SQL tanımı bulunamadı.
                          </Typography>
                        )}
                      </Box>
                    ))}
                  </Box>
                </>
              )}

              {executionDetail.jobInfo && (
                <>
                  <Divider />
                  <JobInfoSection jobInfo={executionDetail.jobInfo} />
                </>
              )}
            </>
          ) : (
            <Alert severity="info">Çalıştırma detayı yüklenemedi.</Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={onCloseDetail}>Kapat</Button>
        </DialogActions>
      </Dialog>
    </AppShell>
  );
}
