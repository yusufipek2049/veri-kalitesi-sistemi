import { useCallback, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Drawer,
  FormControl,
  IconButton,
  InputLabel,
  Link,
  MenuItem,
  Paper,
  Select,
  Skeleton,
  Snackbar,
  TextField,
  Tooltip,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { tr } from "date-fns/locale/tr";
import {
  BadgeCheck,
  Ban,
  Copy,
  Download,
  ListFilter,
  RefreshCw,
  ScrollText,
  Search,
  ShieldCheck,
  ShieldX,
  Wrench,
  X,
  type LucideIcon,
} from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens, type StatusTone } from "../theme/tokens";
import { fetchAuditExport } from "./api";
import { AuditTimeline } from "./AuditTimeline";
import {
  defaultAuditFilters,
  syntheticAuditPage,
  syntheticAuditSummary,
  type AuditEventListItem,
  type AuditEventPage,
  type AuditQueryFilters,
  type AuditState,
  type AuditSummary,
} from "./model";

interface AuditPageProps {
  state?: AuditState;
  page?: AuditEventPage;
  summary?: AuditSummary;
  correlationId?: string;
  onRefresh?: () => void;
  onQuery?: (filters: AuditQueryFilters) => void;
  onLoadMore?: () => void;
  autoRefreshMs?: number;
  newEventCount?: number;
  onAutoRefreshChange?: (intervalMs: number) => void;
  onNewEventsRefresh?: () => void;
}

const resultLabels: Record<string, string> = {
  SUCCESS: "Başarılı",
  FAILURE: "Başarısız",
  DENIED: "Reddedildi",
};

const actionLabels: Record<string, string> = {
  LDAP_AUTHENTICATION: "Kimlik doğrulama",
  DATA_SOURCE_CONNECTION_TEST: "Bağlantı testi",
  RULE_ACTIVATION: "Kural aktivasyonu",
  SCORING_CONFIGURATION_ACTIVATION: "Skor politikası aktivasyonu",
  REPORT_PREVIEW_VIEWED: "Rapor önizleme",
  IDENTITY_SESSION: "Oturum olayı",
  AUDIT_RECORDS_VIEWED: "Denetim kaydı görüntüleme",
  AUDIT_EXPORT_COMPLETED: "Denetim kaydı dışa aktarma",
};

function resultPresentation(result: string): { icon: LucideIcon; tone: StatusTone } {
  if (result === "SUCCESS") return { icon: BadgeCheck, tone: "success" };
  if (result === "DENIED") return { icon: Ban, tone: "warning" };
  return { icon: Wrench, tone: "technical" };
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function localDayBoundary(date: Date, endOfDay: boolean): string {
  const boundary = new Date(
    date.getFullYear(),
    date.getMonth(),
    date.getDate(),
    endOfDay ? 23 : 0,
    endOfDay ? 59 : 0,
    endOfDay ? 59 : 0,
    endOfDay ? 999 : 0,
  );
  if (endOfDay && boundary > new Date()) return new Date().toISOString();
  return boundary.toISOString();
}

function DistributionBar({ count, label, total }: { count: number; label: string; total: number }) {
  const percentage = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <Box sx={{ display: "grid", gap: 0.75 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between" }}>
        <Typography variant="caption">{label}</Typography>
        <Typography variant="caption">{count} · %{percentage}</Typography>
      </Box>
      <Box
        aria-label={`${label}: yüzde ${percentage}`}
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={percentage}
        role="progressbar"
        sx={{ bgcolor: "action.hover", borderRadius: 999, height: 6, overflow: "hidden" }}
      >
        <Box sx={{ bgcolor: "primary.main", height: "100%", width: `${percentage}%` }} />
      </Box>
    </Box>
  );
}

function copyToClipboard(text: string): void {
  void navigator.clipboard.writeText(text);
}

function objectHref(item: Pick<AuditEventListItem, "objectId" | "objectType">): string | null {
  if (!item.objectId) return null;
  if (item.objectType === "QualityRule") return "/rules";
  if (item.objectType === "DataSource") return `/data-sources/${encodeURIComponent(item.objectId)}`;
  if (item.objectType === "DataQualityIssue") return `/issues/${encodeURIComponent(item.objectId)}`;
  if (item.objectType === "ScoringConfiguration") return "/scores";
  return null;
}

function EventRow({
  highlighted,
  item,
  onClick,
  onFilterByObject,
}: {
  highlighted?: boolean;
  item: AuditEventListItem;
  onClick?: (item: AuditEventListItem) => void;
  onFilterByObject?: (item: AuditEventListItem) => void;
}) {
  const presentation = resultPresentation(item.result);
  const Icon = presentation.icon;
  const href = objectHref(item);
  return (
    <Box
      aria-current={highlighted ? "true" : undefined}
      component="li"
      data-event-id={item.eventId}
      onClick={() => onClick?.(item)}
      onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onClick?.(item); } }}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      sx={{
        alignItems: "center",
        borderBottom: 1,
        borderColor: "divider",
        bgcolor: highlighted ? "action.selected" : undefined,
        cursor: onClick ? "pointer" : "default",
        display: "grid",
        gap: 3,
        gridTemplateColumns: {
          xs: "40px minmax(0, 1fr)",
          md: "40px minmax(220px, 1fr) minmax(135px, .55fr) minmax(150px, .62fr)",
          lg: "40px minmax(235px, 1fr) minmax(145px, .58fr) minmax(175px, .7fr) minmax(180px, .72fr) minmax(165px, .66fr)",
        },
        minHeight: 88,
        px: 4,
        py: 3,
        "&:last-child": { borderBottom: 0 },
        "&:hover": onClick ? { bgcolor: "action.hover" } : undefined,
        outline: "none",
        "&:focus-visible": onClick ? { boxShadow: (theme) => `inset 0 0 0 2px ${theme.palette.primary.main}` } : undefined,
      }}
    >
      <Box
        aria-hidden="true"
        data-testid="audit-icon-slot"
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
          {actionLabels[item.action] ?? item.action}
        </Typography>
        <Box sx={{ alignItems: "center", display: "flex", minWidth: 0 }}>
          {href ? (
            <Link
              color="text.secondary"
              href={href}
              noWrap
              onClick={(event) => event.stopPropagation()}
              onKeyDown={(event) => event.stopPropagation()}
              rel="noopener noreferrer"
              target="_blank"
              underline="hover"
              variant="caption"
            >
              {item.objectType} · {item.objectId}
            </Link>
          ) : (
            <Typography color="text.secondary" noWrap variant="caption">
              {item.objectType}{item.objectId ? ` · ${item.objectId}` : ""}
            </Typography>
          )}
          {item.objectId ? (
            <Tooltip title="Bu nesnenin tüm audit kayıtları">
              <IconButton
                aria-label={`${item.objectType} ${item.objectId} için audit kayıtlarını filtrele`}
                onClick={(event) => {
                  event.stopPropagation();
                  onFilterByObject?.(item);
                }}
                onKeyDown={(event) => event.stopPropagation()}
                size="small"
              >
                <ListFilter aria-hidden="true" size={13} />
              </IconButton>
            </Tooltip>
          ) : null}
        </Box>
      </Box>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" } }}>
        <StatusBadge
          label={resultLabels[item.result] ?? item.result}
          tone={presentation.tone}
        />
      </Box>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" }, minWidth: 0 }}>
        <Typography noWrap variant="body2">{item.actorId}</Typography>
        <Typography color="text.secondary" variant="caption">
          {item.actorType ?? "Aktör türü yok"}
        </Typography>
        <Typography
          color="text.secondary"
          sx={{ display: { xs: "block", lg: "none" } }}
          variant="caption"
        >
          {" · "}{formatDate(item.occurredAt)}
        </Typography>
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" }, minWidth: 0 }}>
        <Typography noWrap variant="body2">{item.correlationId}</Typography>
        <Typography color="text.secondary" variant="caption">{item.reasonCode}</Typography>
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" } }}>
        <Typography variant="body2">{formatDate(item.occurredAt)}</Typography>
        <Typography color="text.secondary" variant="caption">Sıra #{item.sequenceNo}</Typography>
      </Box>
    </Box>
  );
}

function StateMessage({
  state,
  correlationId,
  onRefresh,
}: Pick<AuditPageProps, "correlationId" | "onRefresh"> & {
  state: "empty" | "error" | "unauthorized";
}) {
  const content = {
    empty: ["Denetim kaydı bulunamadı", "Seçili filtre ve çevrimiçi dönemle eşleşen kayıt yok."],
    error: ["Denetim kayıtları yüklenemedi", `Teknik bir sorun oluştu. Yeniden deneyin. İzleme kodu: ${correlationId ?? "bulunamadı"}.`],
    unauthorized: ["Bu görünüm için yetkiniz yok", "Denetim olayları ve bütünlük bilgisi gösterilmedi."],
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

function DetailField({ label, children, mono }: { label: string; children: React.ReactNode; mono?: boolean }) {
  return (
    <Box sx={{ mb: 2 }}>
      <Typography color="text.secondary" variant="caption">{label}</Typography>
      <Typography sx={{ fontFamily: mono ? "monospace" : undefined, wordBreak: "break-all" }} variant="body2">{children}</Typography>
    </Box>
  );
}

function EventDetailDrawer({
  item,
  open,
  onClose,
  onFilterByCorrelation,
}: {
  item: AuditEventListItem | null;
  open: boolean;
  onClose: () => void;
  onFilterByCorrelation: (correlationId: string) => void;
}) {
  if (!item) return null;
  const presentation = resultPresentation(item.result);
  const Icon = presentation.icon;
  const hasOldValues = item.oldValueSummary && Object.keys(item.oldValueSummary).length > 0;
  const hasNewValues = item.newValueSummary && Object.keys(item.newValueSummary).length > 0;

  return (
    <Drawer anchor="right" onClose={onClose} open={open} sx={{ "& .MuiDrawer-paper": { width: { xs: "100%", sm: 480 }, p: 0 } }}>
      <Box sx={{ alignItems: "center", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
        <Typography component="h2" variant="h3">Olay detayı</Typography>
        <IconButton aria-label="Kapat" onClick={onClose} size="small"><X size={18} /></IconButton>
      </Box>
      <Divider />
      <Box sx={{ overflow: "auto", px: 4, py: 3 }}>
        <Box sx={{ alignItems: "center", display: "flex", gap: 1.5, mb: 3 }}>
          <Box sx={(theme) => ({ alignItems: "center", bgcolor: theme.status[`${presentation.tone}Surface`], borderRadius: 1, color: theme.status[presentation.tone], display: "flex", height: 40, justifyContent: "center", width: 40 })}>
            <Icon size={20} strokeWidth={1.8} />
          </Box>
          <Box sx={{ minWidth: 0 }}>
            <Typography sx={{ fontWeight: 700 }}>{actionLabels[item.action] ?? item.action}</Typography>
            <StatusBadge label={resultLabels[item.result] ?? item.result} tone={presentation.tone} />
          </Box>
        </Box>

        <DetailField label="Zaman">{formatDate(item.occurredAt)}</DetailField>
        <DetailField label="Sıra no">#{item.sequenceNo}</DetailField>

        <Divider sx={{ my: 2 }} />
        <Typography sx={{ fontWeight: 700, mb: 1.5 }} variant="body2">Aktör</Typography>
        <DetailField label="Aktör ID">{item.actorId}</DetailField>
        <DetailField label="Aktör türü">{item.actorType ?? "Belirtilmemiş"}</DetailField>
        <Box sx={{ mb: 2 }}>
          <Typography color="text.secondary" variant="caption">İlişki kodu</Typography>
          <Box sx={{ alignItems: "center", display: "flex", gap: 1 }}>
            <Typography sx={{ fontFamily: "monospace", wordBreak: "break-all" }} variant="body2">{item.correlationId}</Typography>
            <Tooltip title="Kopyala"><IconButton aria-label="İlişki kodunu kopyala" onClick={() => copyToClipboard(item.correlationId)} size="small"><Copy size={14} /></IconButton></Tooltip>
          </Box>
        </Box>

        <Divider sx={{ my: 2 }} />
        <Typography sx={{ fontWeight: 700, mb: 1.5 }} variant="body2">Nesne</Typography>
        <DetailField label="Nesne türü">{item.objectType}</DetailField>
        <DetailField label="Nesne ID">{item.objectId ?? "—"}</DetailField>
        <DetailField label="Gerekçe kodu">{item.reasonCode}</DetailField>

        {(hasOldValues || hasNewValues) && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography sx={{ fontWeight: 700, mb: 1.5 }} variant="body2">Değer değişiklikleri</Typography>
            {hasOldValues ? (
              <Box sx={{ mb: 2 }}>
                <Typography color="text.secondary" variant="caption">Eski değerler</Typography>
                <Box component="pre" sx={{ bgcolor: "action.hover", borderRadius: 1, fontFamily: "monospace", fontSize: "caption.fontSize", m: 0, overflow: "auto", p: 1.5, whiteSpace: "pre-wrap" }}>
                  {JSON.stringify(item.oldValueSummary, null, 2)}
                </Box>
              </Box>
            ) : null}
            {hasNewValues ? (
              <Box sx={{ mb: 2 }}>
                <Typography color="text.secondary" variant="caption">Yeni değerler</Typography>
                <Box component="pre" sx={{ bgcolor: "action.hover", borderRadius: 1, fontFamily: "monospace", fontSize: "caption.fontSize", m: 0, overflow: "auto", p: 1.5, whiteSpace: "pre-wrap" }}>
                  {JSON.stringify(item.newValueSummary, null, 2)}
                </Box>
              </Box>
            ) : null}
          </>
        )}

        {item.redactedFields.length > 0 && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography sx={{ fontWeight: 700, mb: 1.5 }} variant="body2">Maskelenmiş alanlar</Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
              {item.redactedFields.map((field) => <Chip key={field} label={field} size="small" variant="outlined" />)}
            </Box>
            <Typography color="text.secondary" sx={{ mt: 1 }} variant="caption">{item.redactedFieldCount} alan maskelendi</Typography>
          </>
        )}

        <Divider sx={{ my: 2 }} />
        <Typography sx={{ fontWeight: 700, mb: 1.5 }} variant="body2">Bütünlük</Typography>
        <Box sx={{ mb: 2 }}>
          <Typography color="text.secondary" variant="caption">Olay hash</Typography>
          <Box sx={{ alignItems: "center", display: "flex", gap: 1 }}>
            <Typography sx={{ fontFamily: "monospace", fontSize: "caption.fontSize", wordBreak: "break-all" }} variant="body2">{item.eventHash}</Typography>
            <Tooltip title="Kopyala"><IconButton aria-label="Olay hash'i kopyala" onClick={() => copyToClipboard(item.eventHash)} size="small"><Copy size={14} /></IconButton></Tooltip>
          </Box>
        </Box>
        <Box sx={{ mb: 2 }}>
          <Typography color="text.secondary" variant="caption">Önceki olay hash</Typography>
          <Box sx={{ alignItems: "center", display: "flex", gap: 1 }}>
            <Typography sx={{ fontFamily: "monospace", fontSize: "caption.fontSize", wordBreak: "break-all" }} variant="body2">{item.previousEventHash}</Typography>
            <Tooltip title="Kopyala"><IconButton aria-label="Önceki olay hash'i kopyala" onClick={() => copyToClipboard(item.previousEventHash)} size="small"><Copy size={14} /></IconButton></Tooltip>
          </Box>
        </Box>

        <Divider sx={{ my: 2 }} />
        <Button onClick={() => onFilterByCorrelation(item.correlationId)} startIcon={<Search size={16} />} variant="outlined">
          İlişkili correlation olayları
        </Button>
      </Box>
    </Drawer>
  );
}

function IntegrityDetailDrawer({
  onClose,
  onShowFirstInvalid,
  open,
  page,
}: {
  onClose: () => void;
  onShowFirstInvalid: () => void;
  open: boolean;
  page: AuditEventPage;
}) {
  return (
    <Drawer anchor="right" onClose={onClose} open={open} sx={{ "& .MuiDrawer-paper": { width: { xs: "100%", sm: 440 }, p: 0 } }}>
      <Box sx={{ alignItems: "center", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
        <Typography component="h2" variant="h3">Bütünlük doğrulama sonucu</Typography>
        <IconButton aria-label="Bütünlük detayını kapat" onClick={onClose} size="small"><X size={18} /></IconButton>
      </Box>
      <Divider />
      <Box sx={{ overflow: "auto", px: 4, py: 3 }}>
        <Box sx={{ alignItems: "center", display: "flex", gap: 1.5, mb: 3 }}>
          {page.integrityValid
            ? <ShieldCheck aria-hidden="true" color="currentColor" size={24} />
            : <ShieldX aria-hidden="true" color="currentColor" size={24} />}
          <StatusBadge
            label={page.integrityValid ? "Geçerli" : "Geçersiz"}
            tone={page.integrityValid ? "success" : "critical"}
          />
        </Box>
        <DetailField label="Kontrol edilen kayıt sayısı">{page.integrityCheckedCount}</DetailField>
        <DetailField label="Durum">{page.integrityValid ? "Geçerli" : "Geçersiz"}</DetailField>
        {!page.integrityValid && page.firstInvalidEventId ? (
          <>
            <DetailField label="İlk geçersiz olay ID" mono>{page.firstInvalidEventId}</DetailField>
            <Button onClick={onShowFirstInvalid} startIcon={<Search size={16} />} variant="contained">
              İlk geçersiz olayı gör
            </Button>
          </>
        ) : null}
        <Divider sx={{ my: 3 }} />
        <DetailField label="Politika sürümü">{page.policyVersion}</DetailField>
        <DetailField label="Snapshot sıra numarası">#{page.throughSequenceNo}</DetailField>
        <DetailField label="Snapshot dönemi">{formatDate(page.periodStart)} – {formatDate(page.periodEnd)}</DetailField>
      </Box>
    </Drawer>
  );
}

export function AuditPage({
  state = "normal",
  page = syntheticAuditPage,
  summary = syntheticAuditSummary,
  correlationId,
  onRefresh,
  onQuery,
  onLoadMore,
  autoRefreshMs = 0,
  newEventCount = 0,
  onAutoRefreshChange,
  onNewEventsRefresh,
}: AuditPageProps) {
  const [filters, setFilters] = useState<AuditQueryFilters>(defaultAuditFilters);
  const [selectedEvent, setSelectedEvent] = useState<AuditEventListItem | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [integrityDrawerOpen, setIntegrityDrawerOpen] = useState(false);
  const [highlightedEventId, setHighlightedEventId] = useState<string | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [exportFormat, setExportFormat] = useState<"csv" | "json">("csv");
  const [exporting, setExporting] = useState(false);
  const [exportMessage, setExportMessage] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"list" | "timeline">("list");

  const setPeriodMode = (value: string) => {
    if (value === "custom") {
      const now = new Date();
      const start = new Date(now);
      start.setDate(start.getDate() - 7);
      setFilters((current) => ({
        ...current,
        periodStart: localDayBoundary(start, false),
        periodEnd: now.toISOString(),
      }));
      return;
    }
    setFilters((current) => ({
      ...current,
      days: Number(value),
      periodStart: null,
      periodEnd: null,
    }));
  };

  const handleEventClick = useCallback((item: AuditEventListItem) => {
    setSelectedEvent(item);
    setDrawerOpen(true);
  }, []);

  const handleDrawerClose = useCallback(() => {
    setDrawerOpen(false);
  }, []);

  const handleFilterByCorrelation = useCallback((correlationIdValue: string) => {
    setDrawerOpen(false);
    const nextFilters = { ...defaultAuditFilters, correlationId: correlationIdValue };
    setFilters(nextFilters);
    onQuery?.(nextFilters);
  }, [onQuery]);

  const handleFilterByObject = useCallback((item: AuditEventListItem) => {
    if (!item.objectId) return;
    setDrawerOpen(false);
    const nextFilters = {
      ...defaultAuditFilters,
      objectType: item.objectType,
      objectId: item.objectId,
    };
    setFilters(nextFilters);
    onQuery?.(nextFilters);
  }, [onQuery]);

  const handleShowFirstInvalid = useCallback(() => {
    if (!page.firstInvalidEventId) return;
    const invalidEvent = page.items.find((item) => item.eventId === page.firstInvalidEventId);
    setHighlightedEventId(page.firstInvalidEventId);
    setIntegrityDrawerOpen(false);
    if (invalidEvent) {
      setSelectedEvent(invalidEvent);
      setDrawerOpen(true);
    }
  }, [page.firstInvalidEventId, page.items]);

  const visibleItems = useMemo(
    () => page.items.filter((item) => (
      (!filters.actorId || item.actorId.toLocaleLowerCase("tr-TR").includes(filters.actorId.toLocaleLowerCase("tr-TR")))
      && (!filters.action || item.action.includes(filters.action.toLocaleUpperCase("tr-TR")))
      && (!filters.objectType || item.objectType.toLocaleLowerCase("tr-TR").includes(filters.objectType.toLocaleLowerCase("tr-TR")))
      && (!filters.objectId || item.objectId === filters.objectId)
      && (filters.result === "ALL" || item.result === filters.result)
      && (!filters.correlationId || item.correlationId.toLocaleLowerCase("tr-TR").includes(filters.correlationId.toLocaleLowerCase("tr-TR")))
    )),
    [filters, page.items],
  );
  const effectiveItems = state === "long-content"
    ? Array.from({ length: 5 }, (_, group) => page.items.map((item) => ({
        ...item,
        eventId: `${item.eventId}-${group + 1}`,
        sequenceNo: item.sequenceNo + group * page.items.length,
      }))).flat()
    : visibleItems;
  const topActions = useMemo(
    () => Object.entries(summary.actionDistribution)
      .sort(([leftAction, leftCount], [rightAction, rightCount]) => (
        rightCount - leftCount || leftAction.localeCompare(rightAction, "tr-TR")
      ))
      .slice(0, 5),
    [summary.actionDistribution],
  );
  const applyFilters = () => onQuery?.(filters);
  const resetFilters = () => {
    setFilters(defaultAuditFilters);
    onQuery?.(defaultAuditFilters);
  };
  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await fetchAuditExport(filters, exportFormat);
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = `audit-export-${new Date().toISOString().slice(0, 10)}.${exportFormat}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(downloadUrl);
      setExportOpen(false);
      setExportMessage("Dışa aktarma tamamlandı ve audit loga kaydedildi.");
    } catch {
      setExportMessage("Dışa aktarma tamamlanamadı.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <AppShell currentPage="Denetim">
      <Box sx={(theme) => ({ display: "grid", gap: 5, margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 4, lg: 6 }, width: "100%" })}>
        <Box sx={{ alignItems: { md: "center" }, display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, justifyContent: "space-between" }}>
          <Box>
            <Box sx={{ alignItems: "center", display: "flex", flexWrap: "wrap", gap: 2 }}>
              <Typography component="h1" variant="h1">Denetim</Typography>
              {state !== "unauthorized" ? (
                <ToggleButtonGroup
                  aria-label="Görünüm modu"
                  exclusive
                  onChange={(_event, value: "list" | "timeline" | null) => { if (value) setViewMode(value); }}
                  size="small"
                  value={viewMode}
                >
                  <ToggleButton value="list">Liste</ToggleButton>
                  <ToggleButton value="timeline">Timeline</ToggleButton>
                </ToggleButtonGroup>
              ) : null}
            </Box>
            <Typography color="text.secondary">Yetkili çevrimiçi audit kayıtları ve zincir bütünlüğü</Typography>
          </Box>
          {state !== "unauthorized" ? (
            <Box sx={{ alignItems: "center", display: "flex", flexWrap: "wrap", gap: 2 }}>
              <FormControl size="small" sx={{ minWidth: 150 }}>
                <InputLabel id="audit-auto-refresh-label">Otomatik yenileme</InputLabel>
                <Select
                  label="Otomatik yenileme"
                  labelId="audit-auto-refresh-label"
                  onChange={(event) => onAutoRefreshChange?.(Number(event.target.value))}
                  value={autoRefreshMs}
                >
                  <MenuItem value={0}>Kapalı</MenuItem>
                  <MenuItem value={30_000}>30 sn</MenuItem>
                  <MenuItem value={60_000}>1 dk</MenuItem>
                  <MenuItem value={300_000}>5 dk</MenuItem>
                </Select>
              </FormControl>
              <Button onClick={onRefresh} startIcon={<RefreshCw aria-hidden="true" size={16} />} variant="contained">Yenile</Button>
            </Box>
          ) : null}
        </Box>

        {newEventCount > 0 ? (
          <Alert
            action={<Button color="inherit" onClick={onNewEventsRefresh}>Göster</Button>}
            severity="info"
          >
            {newEventCount} yeni olay yüklendi
          </Alert>
        ) : null}

        {state !== "unauthorized" ? (
          <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
            <Box aria-label="Denetim filtreleri" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(180px, 1fr))", lg: "repeat(3, minmax(155px, 1fr))" } }}>
              <TextField label="Aktör" onChange={(event) => setFilters((current) => ({ ...current, actorId: event.target.value }))} value={filters.actorId} />
              <FormControl><InputLabel id="audit-action-label">İşlem</InputLabel><Select label="İşlem" labelId="audit-action-label" onChange={(event) => setFilters((current) => ({ ...current, action: event.target.value }))} value={filters.action}><MenuItem value="">Tüm işlemler</MenuItem>{Object.entries(actionLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <TextField label="Nesne türü" onChange={(event) => setFilters((current) => ({ ...current, objectType: event.target.value }))} value={filters.objectType} />
              <TextField label="Nesne ID" onChange={(event) => setFilters((current) => ({ ...current, objectId: event.target.value }))} value={filters.objectId} />
              <FormControl><InputLabel id="audit-result-label">Sonuç</InputLabel><Select label="Sonuç" labelId="audit-result-label" onChange={(event) => setFilters((current) => ({ ...current, result: event.target.value }))} value={filters.result}><MenuItem value="ALL">Tüm sonuçlar</MenuItem>{Object.entries(resultLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <FormControl><InputLabel id="audit-period-label">Dönem</InputLabel><Select label="Dönem" labelId="audit-period-label" onChange={(event) => setPeriodMode(event.target.value)} value={filters.periodStart ? "custom" : String(filters.days)}><MenuItem value="1">Son 24 saat</MenuItem><MenuItem value="7">Son 7 gün</MenuItem><MenuItem value="30">Son 30 gün</MenuItem><MenuItem value="custom">Özel aralık</MenuItem></Select></FormControl>
              <TextField label="İlişki kodu" onChange={(event) => setFilters((current) => ({ ...current, correlationId: event.target.value }))} value={filters.correlationId} />
              {filters.periodStart ? (
                <LocalizationProvider adapterLocale={tr} dateAdapter={AdapterDateFns}>
                  <DatePicker
                    label="Başlangıç tarihi"
                    maxDate={filters.periodEnd ? new Date(filters.periodEnd) : new Date()}
                    onChange={(value) => setFilters((current) => ({
                      ...current,
                      periodStart: value ? localDayBoundary(value, false) : null,
                    }))}
                    value={new Date(filters.periodStart)}
                  />
                  <DatePicker
                    label="Bitiş tarihi"
                    maxDate={new Date()}
                    minDate={new Date(filters.periodStart)}
                    onChange={(value) => setFilters((current) => ({
                      ...current,
                      periodEnd: value ? localDayBoundary(value, true) : null,
                    }))}
                    value={filters.periodEnd ? new Date(filters.periodEnd) : null}
                  />
                </LocalizationProvider>
              ) : null}
            </Box>
            <Box sx={{ display: "flex", gap: 2, justifyContent: "flex-end", mt: 3 }}>
              <Button onClick={() => setExportOpen(true)} size="small" startIcon={<Download aria-hidden="true" size={16} />} variant="outlined">Dışa Aktar</Button>
              <Button onClick={resetFilters} size="small">Filtreleri temizle</Button>
              <Button onClick={applyFilters} size="small" variant="contained">Uygula</Button>
            </Box>
          </Paper>
        ) : null}

        {state === "loading" ? <Box aria-busy="true" aria-label="Denetim kayıtları yükleniyor">{Array.from({ length: 6 }, (_, index) => <Skeleton height={88} key={index} />)}</Box> : null}
        {state === "empty" || state === "error" || state === "unauthorized" ? <StateMessage correlationId={correlationId} onRefresh={onRefresh} state={state} /> : null}

        {(state === "normal" || state === "long-content") ? (
          <>
            <Box aria-label="Denetim özeti" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" } }}>
              <Paper
                component="button"
                onClick={() => setIntegrityDrawerOpen(true)}
                sx={(theme) => ({
                  bgcolor: theme.status[page.integrityValid ? "successSurface" : "criticalSurface"],
                  borderColor: theme.status[page.integrityValid ? "success" : "critical"],
                  borderRadius: 1.5,
                  color: theme.status[page.integrityValid ? "success" : "critical"],
                  minHeight: 116,
                  p: 4,
                  cursor: "pointer",
                  font: "inherit",
                  textAlign: "left",
                  width: "100%",
                  "& .MuiTypography-root": { color: "inherit" },
                })}
                variant="outlined"
              >
                {page.integrityValid ? <ShieldCheck aria-hidden="true" size={20} /> : <ShieldX aria-hidden="true" size={20} />}
                <Typography sx={{ mt: 2 }} variant="h3">{page.integrityValid ? "Bütünlük doğrulandı" : "Bütünlük sorunu"}</Typography>
                <Typography variant="caption">{page.integrityCheckedCount} kayıt kontrol edildi</Typography>
              </Paper>
              <Paper component="section" sx={{ borderRadius: 1.5, minHeight: 116, p: 4 }} variant="outlined">
                <ScrollText aria-hidden="true" size={20} />
                <Typography sx={{ mt: 2 }} variant="h2">{effectiveItems.length}</Typography>
                <Typography color="text.secondary" variant="caption">Görüntülenen olay · sayfa sınırı {page.pageSize}</Typography>
              </Paper>
              <Paper component="section" sx={{ borderRadius: 1.5, minHeight: 116, p: 4 }} variant="outlined">
                <Typography color="text.secondary" variant="body2">Çevrimiçi dönem</Typography>
                <Typography sx={{ mt: 2 }} variant="h3">{filters.periodStart ? "Özel aralık" : `${filters.days} gün`}</Typography>
                <Typography color="text.secondary" variant="caption">Snapshot #{page.throughSequenceNo} · {page.policyVersion}</Typography>
              </Paper>
            </Box>

            <Box aria-label="Özet istatistikleri" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", lg: "repeat(3, minmax(0, 1fr))" } }}>
              <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
                <Typography component="h2" variant="h3">Sonuç dağılımı</Typography>
                <Typography color="text.secondary" sx={{ mb: 2 }} variant="caption">Toplam {summary.totalCount} olay</Typography>
                <Box sx={{ display: "grid", gap: 2, mt: 2 }}>
                  {(["SUCCESS", "FAILURE", "DENIED"] as const).map((result) => (
                    <DistributionBar
                      count={summary.resultDistribution[result] ?? 0}
                      key={result}
                      label={result}
                      total={summary.totalCount}
                    />
                  ))}
                </Box>
              </Paper>
              <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
                <Typography component="h2" variant="h3">En sık işlemler</Typography>
                <Box component="ol" sx={{ display: "grid", gap: 1.5, listStyle: "none", m: 0, mt: 2, p: 0 }}>
                  {topActions.map(([action, count]) => (
                    <Box component="li" key={action} sx={{ display: "flex", gap: 2, justifyContent: "space-between" }}>
                      <Typography noWrap variant="body2">{action}</Typography>
                      <Typography sx={{ fontWeight: 700 }} variant="body2">{count}</Typography>
                    </Box>
                  ))}
                  {topActions.length === 0 ? <Typography color="text.secondary" variant="body2">Veri yok</Typography> : null}
                </Box>
              </Paper>
              <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
                <Typography component="h2" variant="h3">En aktif aktörler</Typography>
                <Box component="ol" sx={{ display: "grid", gap: 1.5, listStyle: "none", m: 0, mt: 2, p: 0 }}>
                  {summary.topActors.map((actor) => (
                    <Box component="li" key={actor.actorId} sx={{ display: "flex", gap: 2, justifyContent: "space-between" }}>
                      <Typography noWrap variant="body2">{actor.actorId}</Typography>
                      <Typography sx={{ fontWeight: 700 }} variant="body2">{actor.count}</Typography>
                    </Box>
                  ))}
                  {summary.topActors.length === 0 ? <Typography color="text.secondary" variant="body2">Veri yok</Typography> : null}
                </Box>
              </Paper>
            </Box>

            {!page.integrityValid ? <Alert severity="error"><Typography sx={{ fontWeight: 700 }}>Audit zinciri bütünlük kontrolünden geçmedi</Typography><Typography variant="body2">Kayıtlar değiştirilmedi. Güvenlik incelemesi gereklidir.</Typography></Alert> : null}

            {effectiveItems.length === 0 ? <StateMessage state="empty" /> : viewMode === "timeline" ? (
              <Paper component="section" sx={{ borderRadius: 1.5, overflow: "hidden" }} variant="outlined">
                <Box sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
                  <Box>
                    <Typography component="h2" variant="h3">Audit Timeline</Typography>
                    <Typography color="text.secondary" variant="caption">{formatDate(page.periodStart)} – {formatDate(page.periodEnd)}</Typography>
                  </Box>
                  <Typography color="text.secondary" variant="body2">{effectiveItems.length} kayıt</Typography>
                </Box>
                <Box sx={{ p: 4 }}><AuditTimeline items={effectiveItems} onSelect={handleEventClick} /></Box>
              </Paper>
            ) : (
              <Paper component="section" sx={{ borderRadius: 1.5, overflow: "hidden" }} variant="outlined">
                <Box sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
                  <Box>
                    <Typography component="h2" variant="h3">Audit Olayları</Typography>
                    <Typography color="text.secondary" variant="caption">{formatDate(page.periodStart)} – {formatDate(page.periodEnd)}</Typography>
                  </Box>
                  <Typography color="text.secondary" variant="body2">{effectiveItems.length} kayıt</Typography>
                </Box>
                <Box aria-hidden="true" sx={{ borderBottom: 1, borderColor: "divider", color: "text.secondary", display: { xs: "none", lg: "grid" }, fontSize: "caption.fontSize", fontWeight: 700, gap: 3, gridTemplateColumns: "40px minmax(235px, 1fr) minmax(145px, .58fr) minmax(175px, .7fr) minmax(180px, .72fr) minmax(165px, .66fr)", px: 4, py: 2 }}>
                  <Box /><Box>İşlem ve nesne</Box><Box>Sonuç</Box><Box>Aktör</Box><Box>İlişki ve gerekçe</Box><Box>Zaman</Box>
                </Box>
                <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>{effectiveItems.map((item) => <EventRow highlighted={item.eventId === highlightedEventId} item={item} key={item.eventId} onClick={handleEventClick} onFilterByObject={handleFilterByObject} />)}</Box>
                {page.nextAfterSequenceNo !== null ? <Box sx={{ borderTop: 1, borderColor: "divider", display: "flex", justifyContent: "center", p: 3 }}><Button onClick={onLoadMore}>Daha fazla göster</Button></Box> : null}
              </Paper>
            )}
          </>
        ) : null}
      </Box>
      <EventDetailDrawer item={selectedEvent} open={drawerOpen} onClose={handleDrawerClose} onFilterByCorrelation={handleFilterByCorrelation} />
      <IntegrityDetailDrawer onClose={() => setIntegrityDrawerOpen(false)} onShowFirstInvalid={handleShowFirstInvalid} open={integrityDrawerOpen} page={page} />
      <Dialog onClose={() => setExportOpen(false)} open={exportOpen}>
        <DialogTitle>Denetim kayıtlarını dışa aktar</DialogTitle>
        <DialogContent sx={{ minWidth: { sm: 360 }, pt: "12px !important" }}>
          <FormControl fullWidth>
            <InputLabel id="audit-export-format-label">Format</InputLabel>
            <Select
              label="Format"
              labelId="audit-export-format-label"
              onChange={(event) => setExportFormat(event.target.value as "csv" | "json")}
              value={exportFormat}
            >
              <MenuItem value="csv">CSV</MenuItem>
              <MenuItem value="json">JSON</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button disabled={exporting} onClick={() => setExportOpen(false)}>Vazgeç</Button>
          <Button disabled={exporting} onClick={() => void handleExport()} variant="contained">{exporting ? "Hazırlanıyor…" : "İndir"}</Button>
        </DialogActions>
      </Dialog>
      <Snackbar
        autoHideDuration={5000}
        message={exportMessage ?? ""}
        onClose={() => setExportMessage(null)}
        open={exportMessage !== null}
      />
    </AppShell>
  );
}
