import { useCallback, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Drawer,
  FormControl,
  IconButton,
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
  AlertCircle,
  AlertTriangle,
  Bell,
  Check,
  CheckCheck,
  Inbox as InboxIcon,
  Info,
  RefreshCw,
  Search,
  X,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { type StatusTone } from "../theme/tokens";
import type {
  NotificationDelivery,
  NotificationDeliveryStatus,
  NotificationEventType,
  NotificationSeverity,
} from "./model";

export type NotificationsPageState =
  | "normal"
  | "loading"
  | "empty"
  | "error"
  | "unauthorized";

interface NotificationsPageProps {
  state?: NotificationsPageState;
  items?: NotificationDelivery[];
  totalUnread?: number;
  failedCount?: number;
  todayCount?: number;
  cursor?: string | null;
  hasMore?: boolean;
  correlationId?: string;
  onRefresh?: () => void;
  onMarkRead?: (deliveryId: string) => void;
  onMarkAllRead?: () => void;
  onBulkMarkRead?: (deliveryIds: string[]) => void;
  onFilterChange?: (filters: NotificationFilters) => void;
  onLoadMore?: () => void;
}

export interface NotificationFilters {
  status: "ALL" | NotificationDeliveryStatus;
  eventType: "ALL" | NotificationEventType;
  search: string;
}

const defaultFilters: NotificationFilters = {
  status: "ALL",
  eventType: "ALL",
  search: "",
};

const statusLabels: Record<string, string> = {
  ALL: "Tüm durumlar",
  PENDING: "Bekliyor",
  SENDING: "Gönderiliyor",
  DELIVERED: "Teslim edildi",
  FAILED: "Başarısız",
  UNDELIVERABLE: "Teslim edilemez",
  REROUTED: "Yönlendirildi",
  READ: "Okundu",
};

const eventTypeLabels: Record<string, string> = {
  ALL: "Tüm olaylar",
  QUALITY_THRESHOLD: "Kalite eşiği",
  CRITICAL_RULE_FAILURE: "Kritik kural hatası",
  TECHNICAL_ERROR: "Teknik hata",
  ISSUE_ASSIGNED: "Sorun ataması",
  RULE_APPROVAL_REQUESTED: "Kural onay talebi",
  RULE_APPROVAL_DECIDED: "Onay kararı",
  RULE_APPROVAL_WITHDRAWN: "Onay geri çekme",
  RULE_APPROVAL_EXPIRED: "Onay süresi doldu",
};

const severityConfig: Record<NotificationSeverity, { color: string; icon: typeof AlertTriangle }> = {
  CRITICAL: { color: "#d32f2f", icon: AlertTriangle },
  WARNING: { color: "#ed6c02", icon: AlertCircle },
  ACTION_REQUIRED: { color: "#0288d1", icon: AlertCircle },
  INFO: { color: "#2e7d32", icon: Info },
};

function statusTone(status: NotificationDeliveryStatus): StatusTone {
  switch (status) {
    case "DELIVERED":
    case "READ":
      return "success";
    case "FAILED":
    case "UNDELIVERABLE":
      return "critical";
    case "SENDING":
    case "REROUTED":
      return "warning";
    case "PENDING":
      return "technical";
    default:
      return "technical";
  }
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatEventTitle(
  eventType: NotificationEventType | string,
  payload?: Record<string, unknown>,
): string {
  switch (eventType) {
    case "RULE_APPROVAL_REQUESTED":
      return `Kural Onay Talebi: ${payload?.rule_code ?? ""} - ${payload?.rule_name ?? ""}`;
    case "RULE_APPROVAL_DECIDED":
      return `Onay Kararı: ${payload?.rule_code ?? ""} - ${payload?.decision ?? ""}`;
    case "RULE_APPROVAL_WITHDRAWN":
      return `Onay Geri Çekme: ${payload?.rule_code ?? ""} - ${payload?.rule_name ?? ""}`;
    case "RULE_APPROVAL_EXPIRED":
      return `Onay Süresi Doldu: ${payload?.rule_code ?? ""} - ${payload?.rule_name ?? ""}`;
    default:
      return eventTypeLabels[eventType] ?? eventType;
  }
}

const scopeTypeLabels: Record<string, string> = {
  DATASET: "Dataset",
  SOURCE: "Veri kaynağı",
  RULE: "Kural",
  EXECUTION: "Çalıştırma",
  ISSUE_ASSIGNMENT: "Sorun ataması",
};

function deliveryScopeLink(item: NotificationDelivery): string | null {
  if (item.scopeType === "DATASET" && item.scopeId) {
    return `/catalog/datasets/${item.scopeId}`;
  }
  if (item.scopeType === "SOURCE") {
    return "/data-sources";
  }
  if (item.scopeType === "RULE") {
    return "/rules";
  }
  if (item.scopeType === "ISSUE_ASSIGNMENT" && item.scopeId) {
    return `/issues?selected=${encodeURIComponent(item.scopeId)}`;
  }
  if (item.scopeType === "EXECUTION" && item.scopeId) {
    return `/executions?selected=${encodeURIComponent(item.scopeId)}`;
  }
  return null;
}

// Date grouping utility
type DateGroup = { label: string; items: NotificationDelivery[] };

function groupByDate(items: NotificationDelivery[]): DateGroup[] {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);

  const groups: Record<string, NotificationDelivery[]> = {
    "Bugün": [],
    "Dün": [],
    "Bu Hafta": [],
    "Daha Eski": [],
  };

  for (const item of items) {
    const d = new Date(item.createdAt);
    if (d >= today) {
      groups["Bugün"].push(item);
    } else if (d >= yesterday) {
      groups["Dün"].push(item);
    } else if (d >= weekAgo) {
      groups["Bu Hafta"].push(item);
    } else {
      groups["Daha Eski"].push(item);
    }
  }

  return Object.entries(groups)
    .filter(([, arr]) => arr.length > 0)
    .map(([label, arr]) => ({ label, items: arr }));
}

function SeverityIcon({ severity }: { severity: NotificationSeverity | null }) {
  if (!severity) return null;
  const config = severityConfig[severity];
  if (!config) return null;
  const Icon = config.icon;
  return <Icon aria-hidden="true" size={16} style={{ color: config.color, flexShrink: 0 }} />;
}

function DeliveryRow({
  item,
  onMarkRead,
  selected,
  onSelect,
  onOpenDetail,
}: {
  item: NotificationDelivery;
  onMarkRead?: (id: string) => void;
  selected?: boolean;
  onSelect?: (id: string, checked: boolean) => void;
  onOpenDetail?: (item: NotificationDelivery) => void;
}) {
  const tone = statusTone(item.status);
  const isRead = item.status === "READ";
  const isUnread = !isRead && item.status !== "FAILED" && item.status !== "UNDELIVERABLE";
  const canMarkRead = item.status === "DELIVERED";
  const title = item.eventType
    ? formatEventTitle(item.eventType, item.payload)
    : `Teslimat ${item.deliveryId.slice(0, 12)}`;
  const scopeLabel = item.scopeType && item.scopeId
    ? `${scopeTypeLabels[item.scopeType] ?? item.scopeType}: ${item.scopeId.length > 24 ? `${item.scopeId.slice(0, 22)}…` : item.scopeId}`
    : null;
  const scopeLink = deliveryScopeLink(item);

  return (
    <Box
      component="li"
      sx={{
        alignItems: "center",
        borderBottom: 1,
        borderColor: "divider",
        borderLeft: isUnread ? "3px solid" : "3px solid transparent",
        borderLeftColor: isUnread ? "primary.main" : "transparent",
        display: "grid",
        gap: 2,
        gridTemplateColumns: {
          xs: "auto minmax(0, 1fr) auto",
          md: "auto minmax(180px, .8fr) minmax(140px, .5fr) minmax(140px, .5fr) minmax(150px, .6fr) auto",
        },
        minHeight: 72,
        px: 3,
        py: 2.5,
        "&:last-child": { borderBottom: 0 },
        "&:hover": { bgcolor: "action.hover" },
      }}
    >
      <Checkbox
        checked={selected ?? false}
        onChange={(e) => onSelect?.(item.deliveryId, e.target.checked)}
        size="small"
        sx={{ py: 0, px: 0.5 }}
      />
      <Box sx={{ minWidth: 0, cursor: onOpenDetail ? "pointer" : "default" }} onClick={() => onOpenDetail?.(item)}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <SeverityIcon severity={item.severity} />
          <Typography noWrap sx={{ fontWeight: isRead ? 400 : 700 }} variant="body2">
            {title}
          </Typography>
        </Box>
        {scopeLabel ? (
          scopeLink ? (
            <Typography
              component={Link}
              color="primary.main"
              noWrap
              sx={{ textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
              to={scopeLink}
              variant="caption"
            >
              {scopeLabel}
            </Typography>
          ) : (
            <Typography color="text.secondary" noWrap variant="caption">
              {scopeLabel}
            </Typography>
          )
        ) : (
          <Typography color="text.secondary" noWrap variant="caption">
            Olay {item.eventId.slice(0, 12)}
          </Typography>
        )}
      </Box>
      <Box sx={{ gridColumn: { xs: "1", md: "auto" } }}>
        <StatusBadge label={statusLabels[item.status] ?? item.status} tone={tone} />
      </Box>
      <Box sx={{ display: { xs: "none", md: "block" }, minWidth: 0 }}>
        <Typography color="text.secondary" variant="caption">
          Deneme {item.attemptCount}
        </Typography>
      </Box>
      <Box sx={{ display: { xs: "none", md: "block" } }}>
        <Typography variant="caption">{formatDate(item.createdAt)}</Typography>
        {item.deliveredAt ? (
          <Typography color="text.secondary" variant="caption">
            {" · "}Teslim: {formatDate(item.deliveredAt)}
          </Typography>
        ) : null}
      </Box>
      <Box sx={{ display: "flex", gap: 0.5 }}>
        {canMarkRead ? (
          <Button
            onClick={() => onMarkRead?.(item.deliveryId)}
            size="small"
            startIcon={<Check aria-hidden="true" size={14} />}
            variant="outlined"
          >
            Okundu
          </Button>
        ) : isRead ? (
          <Chip label="Okundu" size="small" sx={{ fontWeight: 600 }} />
        ) : null}
      </Box>
    </Box>
  );
}

function DetailDrawer({
  item,
  open,
  onClose,
}: {
  item: NotificationDelivery | null;
  open: boolean;
  onClose: () => void;
}) {
  if (!item) return null;
  const title = item.eventType
    ? formatEventTitle(item.eventType, item.payload)
    : `Teslimat ${item.deliveryId.slice(0, 12)}`;
  const scopeLabel = item.scopeType && item.scopeId
    ? `${scopeTypeLabels[item.scopeType] ?? item.scopeType}: ${item.scopeId}`
    : null;
  const scopeLink = deliveryScopeLink(item);

  const payloadEntries = Object.entries(item.payload ?? {}).filter(
    ([k]) => !["password", "secret", "token", "credential"].includes(k.toLowerCase()),
  );

  return (
    <Drawer
      anchor="right"
      onClose={onClose}
      open={open}
      sx={{ "& .MuiDrawer-paper": { width: { xs: "100%", sm: 420 }, p: 3 } }}
    >
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Typography component="h2" variant="h2">
          Bildirim Detayı
        </Typography>
        <IconButton onClick={onClose} size="small">
          <X size={18} />
        </IconButton>
      </Box>

      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
        <SeverityIcon severity={item.severity} />
        <Typography sx={{ fontWeight: 700 }} variant="body1">
          {title}
        </Typography>
      </Box>

      <Box sx={{ mb: 3 }}>
        <StatusBadge label={statusLabels[item.status] ?? item.status} tone={statusTone(item.status)} />
      </Box>

      {/* Timeline */}
      <Box sx={{ mb: 3 }}>
        <Typography sx={{ fontWeight: 700, mb: 1 }} variant="body2">
          Zaman Çizelgesi
        </Typography>
        <Box sx={{ display: "grid", gap: 1, pl: 2, borderLeft: 2, borderColor: "divider" }}>
          <Box>
            <Typography color="text.secondary" variant="caption">Oluşturulma</Typography>
            <Typography variant="body2">{formatDate(item.createdAt)}</Typography>
          </Box>
          {item.deliveredAt ? (
            <Box>
              <Typography color="text.secondary" variant="caption">Teslim</Typography>
              <Typography variant="body2">{formatDate(item.deliveredAt)}</Typography>
            </Box>
          ) : null}
          {item.readAt ? (
            <Box>
              <Typography color="text.secondary" variant="caption">Okundu</Typography>
              <Typography variant="body2">{formatDate(item.readAt)}</Typography>
            </Box>
          ) : null}
        </Box>
      </Box>

      {/* Scope */}
      {scopeLabel ? (
        <Box sx={{ mb: 3 }}>
          <Typography sx={{ fontWeight: 700, mb: 0.5 }} variant="body2">
            Kapsam
          </Typography>
          {scopeLink ? (
            <Typography
              component={Link}
              color="primary.main"
              sx={{ textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
              to={scopeLink}
              variant="body2"
            >
              {scopeLabel}
            </Typography>
          ) : (
            <Typography color="text.secondary" variant="body2">
              {scopeLabel}
            </Typography>
          )}
        </Box>
      ) : null}

      {/* Payload */}
      {payloadEntries.length > 0 ? (
        <Box sx={{ mb: 3 }}>
          <Typography sx={{ fontWeight: 700, mb: 1 }} variant="body2">
            Olay Detayları
          </Typography>
          <Paper sx={{ p: 2, bgcolor: "grey.50" }} variant="outlined">
            {payloadEntries.map(([key, value]) => (
              <Box key={key} sx={{ display: "flex", gap: 1, mb: 0.5 }}>
                <Typography color="text.secondary" sx={{ fontWeight: 600, minWidth: 120 }} variant="caption">
                  {key}:
                </Typography>
                <Typography variant="caption">
                  {typeof value === "object" ? JSON.stringify(value) : String(value)}
                </Typography>
              </Box>
            ))}
          </Paper>
        </Box>
      ) : null}

      {/* Delivery metadata */}
      <Box>
        <Typography sx={{ fontWeight: 700, mb: 0.5 }} variant="body2">
          Teslimat Bilgileri
        </Typography>
        <Typography color="text.secondary" variant="caption">
          Delivery ID: {item.deliveryId.slice(0, 16)}…
        </Typography>
        <Typography color="text.secondary" variant="caption" sx={{ display: "block" }}>
          Deneme sayısı: {item.attemptCount}
        </Typography>
      </Box>
    </Drawer>
  );
}

function StateMessage({
  state,
  correlationId,
  onRefresh,
}: {
  state: "empty" | "error" | "unauthorized";
  correlationId?: string;
  onRefresh?: () => void;
}) {
  const content = {
    empty: ["Gelen kutusu boş", "Şu anda bekleyen veya okunmamış bildirim bulunmuyor."],
    error: [
      "Bildirimler yüklenemedi",
      `Teknik bir sorun oluştu. Yeniden deneyin. İzleme kodu: ${correlationId ?? "bulunamadı"}.`,
    ],
    unauthorized: ["Bu görünüm için yetkiniz yok", "Bildirim kutunuz gösterilmedi."],
  }[state];
  return (
    <Alert
      action={
        state === "error" ? (
          <Button color="inherit" onClick={onRefresh}>
            Yeniden dene
          </Button>
        ) : undefined
      }
      severity={state === "error" ? "error" : state === "unauthorized" ? "warning" : "info"}
    >
      <Typography sx={{ fontWeight: 700 }}>{content[0]}</Typography>
      <Typography variant="body2">{content[1]}</Typography>
    </Alert>
  );
}

export function NotificationsPage({
  state = "normal",
  items = [],
  totalUnread = 0,
  failedCount = 0,
  todayCount = 0,
  hasMore = false,
  correlationId,
  onRefresh,
  onMarkRead,
  onMarkAllRead,
  onBulkMarkRead,
  onFilterChange,
  onLoadMore,
}: NotificationsPageProps) {
  const [filters, setFilters] = useState<NotificationFilters>(defaultFilters);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [drawerItem, setDrawerItem] = useState<NotificationDelivery | null>(null);
  const location = useLocation();

  const notificationTabs = [
    { label: "Gelen Kutusu", path: "/notifications" },
    { label: "Tercihler", path: "/notifications/preferences" },
    { label: "Kanallar", path: "/notifications/channels" },
    { label: "Teslimatlar", path: "/notifications/deliveries" },
  ];
  const currentTab = notificationTabs.findIndex((t) => t.path === location.pathname);

  const visibleItems = useMemo(
    () =>
      items.filter((item) => {
        if (filters.status !== "ALL" && item.status !== filters.status) return false;
        if (filters.eventType !== "ALL" && item.eventType !== filters.eventType) return false;
        if (filters.search) {
          const q = filters.search.toLowerCase();
          const title = item.eventType
            ? formatEventTitle(item.eventType, item.payload).toLowerCase()
            : "";
          const scope = item.scopeId?.toLowerCase() ?? "";
          const eventType = item.eventType?.toLowerCase() ?? "";
          if (!title.includes(q) && !scope.includes(q) && !eventType.includes(q)) return false;
        }
        return true;
      }),
    [filters, items],
  );

  const dateGroups = useMemo(() => groupByDate(visibleItems), [visibleItems]);

  const applyFilters = () => onFilterChange?.(filters);
  const resetFilters = () => {
    setFilters(defaultFilters);
    onFilterChange?.(defaultFilters);
  };

  const handleSelect = useCallback((id: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    setSelectedIds((prev) => {
      if (prev.size === visibleItems.length) return new Set();
      return new Set(visibleItems.map((i) => i.deliveryId));
    });
  }, [visibleItems]);

  const handleBulkMarkRead = useCallback(() => {
    const readableIds = visibleItems
      .filter((i) => i.status === "DELIVERED" && selectedIds.has(i.deliveryId))
      .map((i) => i.deliveryId);
    if (readableIds.length > 0) {
      onBulkMarkRead?.(readableIds);
      setSelectedIds(new Set());
    }
  }, [visibleItems, selectedIds, onBulkMarkRead]);

  const hasSelection = selectedIds.size > 0;

  return (
    <AppShell currentPage="Bildirimler">
      <Box
        sx={(theme) => ({
          display: "grid",
          gap: 5,
          margin: "0 auto",
          maxWidth: theme.appLayout.contentMaxWidth,
          p: { xs: 3, md: 4, lg: 6 },
          width: "100%",
        })}
      >
        {/* Header */}
        <Box
          sx={{
            alignItems: { md: "center" },
            display: "flex",
            flexDirection: { xs: "column", md: "row" },
            gap: 3,
            justifyContent: "space-between",
          }}
        >
          <Box>
            <Typography component="h1" variant="h1">
              Bildirimler
            </Typography>
            <Typography color="text.secondary">
              Gelen kutusu, teslimat durumu ve okuma aksiyonları
            </Typography>
          </Box>
          <Box sx={{ display: "flex", gap: 2 }}>
            {state !== "unauthorized" ? (
              <>
                {totalUnread > 0 ? (
                  <Button
                    onClick={onMarkAllRead}
                    startIcon={<CheckCheck aria-hidden="true" size={16} />}
                    variant="outlined"
                  >
                    Tümünü okundu işaretle
                  </Button>
                ) : null}
                <Button
                  onClick={onRefresh}
                  startIcon={<RefreshCw aria-hidden="true" size={16} />}
                  variant="contained"
                >
                  Yenile
                </Button>
              </>
            ) : null}
          </Box>
        </Box>

        {/* Sub-navigation tabs */}
        <Tabs
          value={currentTab >= 0 ? currentTab : 0}
          sx={{ borderBottom: 1, borderColor: "divider" }}
        >
          {notificationTabs.map((tab) => (
            <Tab
              key={tab.path}
              label={tab.label}
              component={Link}
              to={tab.path}
              sx={{ textTransform: "none", fontWeight: 600 }}
            />
          ))}
        </Tabs>

        {/* Filters */}
        {state !== "unauthorized" ? (
          <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
            <Box
              aria-label="Bildirim filtreleri"
              sx={{
                display: "grid",
                gap: 3,
                gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(180px, 1fr))" },
              }}
            >
              <FormControl>
                <InputLabel id="notification-status-label">Durum</InputLabel>
                <Select
                  label="Durum"
                  labelId="notification-status-label"
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      status: event.target.value as NotificationFilters["status"],
                    }))
                  }
                  value={filters.status}
                >
                  {Object.entries(statusLabels).map(([value, label]) => (
                    <MenuItem key={value} value={value}>
                      {label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl>
                <InputLabel id="notification-event-type-label">Olay türü</InputLabel>
                <Select
                  label="Olay türü"
                  labelId="notification-event-type-label"
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      eventType: event.target.value as NotificationFilters["eventType"],
                    }))
                  }
                  value={filters.eventType}
                >
                  {Object.entries(eventTypeLabels).map(([value, label]) => (
                    <MenuItem key={value} value={value}>
                      {label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                slotProps={{
                  input: {
                    startAdornment: <Search aria-hidden="true" size={16} style={{ marginRight: 8 }} />,
                  },
                }}
                label="Ara"
                onChange={(event) =>
                  setFilters((current) => ({ ...current, search: event.target.value }))
                }
                placeholder="Bildirim ara…"
                value={filters.search}
              />
            </Box>
            <Box sx={{ display: "flex", gap: 2, justifyContent: "flex-end", mt: 3 }}>
              <Button onClick={resetFilters} size="small">
                Filtreleri temizle
              </Button>
              <Button onClick={applyFilters} size="small" variant="contained">
                Uygula
              </Button>
            </Box>
          </Paper>
        ) : null}

        {/* Loading */}
        {state === "loading" ? (
          <Box aria-busy="true" aria-label="Bildirimler yükleniyor">
            {Array.from({ length: 5 }, (_, index) => (
              <Skeleton height={72} key={index} />
            ))}
          </Box>
        ) : null}

        {/* Error states */}
        {state === "empty" || state === "error" || state === "unauthorized" ? (
          <StateMessage
            correlationId={correlationId}
            onRefresh={onRefresh}
            state={state}
          />
        ) : null}

        {/* Normal state */}
        {state === "normal" ? (
          <>
            {/* Summary cards */}
            <Box
              aria-label="Bildirim özeti"
              sx={{
                display: "grid",
                gap: 3,
                gridTemplateColumns: { xs: "1fr", md: "repeat(5, minmax(0, 1fr))" },
              }}
            >
              <Paper
                component="section"
                sx={(theme) => ({
                  bgcolor: theme.status.successSurface,
                  borderColor: theme.status.success,
                  borderRadius: 1.5,
                  color: theme.status.success,
                  minHeight: 100,
                  p: 4,
                  "& .MuiTypography-root": { color: "inherit" },
                })}
                variant="outlined"
              >
                <Bell aria-hidden="true" size={20} />
                <Typography sx={{ mt: 2 }} variant="h2">
                  {totalUnread}
                </Typography>
                <Typography variant="caption">Okunmamış bildirim</Typography>
              </Paper>
              <Paper
                component="section"
                sx={{ borderRadius: 1.5, minHeight: 100, p: 4 }}
                variant="outlined"
              >
                <InboxIcon aria-hidden="true" size={20} />
                <Typography sx={{ mt: 2 }} variant="h2">
                  {visibleItems.length}
                </Typography>
                <Typography color="text.secondary" variant="caption">
                  Görüntülenen teslimat
                </Typography>
              </Paper>
              <Paper
                component="section"
                sx={(theme) => ({
                  borderRadius: 1.5,
                  minHeight: 100,
                  p: 4,
                  bgcolor: theme.status.criticalSurface,
                  borderColor: theme.status.critical,
                })}
                variant="outlined"
              >
                <AlertTriangle aria-hidden="true" size={20} style={{ color: "#d32f2f" }} />
                <Typography sx={{ mt: 2 }} variant="h2">
                  {failedCount}
                </Typography>
                <Typography color="text.secondary" variant="caption">
                  Başarısız teslimat
                </Typography>
              </Paper>
              <Paper
                component="section"
                sx={{ borderRadius: 1.5, minHeight: 100, p: 4 }}
                variant="outlined"
              >
                <Info aria-hidden="true" size={20} style={{ color: "#0288d1" }} />
                <Typography sx={{ mt: 2 }} variant="h2">
                  {todayCount}
                </Typography>
                <Typography color="text.secondary" variant="caption">
                  Bugünkü bildirimler
                </Typography>
              </Paper>
              <Paper
                component="section"
                sx={{ borderRadius: 1.5, minHeight: 100, p: 4 }}
                variant="outlined"
              >
                <Typography color="text.secondary" variant="body2">
                  Gelen kutusu
                </Typography>
                <Typography sx={{ mt: 2 }} variant="h3">
                  {filters.status === "ALL" ? "Tümü" : statusLabels[filters.status] ?? filters.status}
                </Typography>
                <Typography color="text.secondary" variant="caption">
                  Filtre: {filters.eventType === "ALL" ? "Tüm olaylar" : eventTypeLabels[filters.eventType] ?? filters.eventType}
                </Typography>
              </Paper>
            </Box>

            {/* Bulk action toolbar */}
            {hasSelection ? (
              <Paper
                sx={{
                  alignItems: "center",
                  borderRadius: 1.5,
                  display: "flex",
                  gap: 2,
                  justifyContent: "space-between",
                  p: 2,
                }}
                variant="outlined"
              >
                <Typography variant="body2">
                  {selectedIds.size} öğe seçildi
                </Typography>
                <Box sx={{ display: "flex", gap: 1 }}>
                  <Button
                    onClick={handleBulkMarkRead}
                    size="small"
                    startIcon={<Check aria-hidden="true" size={14} />}
                    variant="contained"
                  >
                    Seçilenleri okundu işaretle
                  </Button>
                  <Button
                    onClick={() => setSelectedIds(new Set())}
                    size="small"
                  >
                    Seçimi temizle
                  </Button>
                </Box>
              </Paper>
            ) : null}

            {/* Inbox list */}
            {visibleItems.length === 0 ? (
              <StateMessage state="empty" />
            ) : (
              <Paper
                component="section"
                sx={{ borderRadius: 1.5, overflow: "hidden" }}
                variant="outlined"
              >
                <Box
                  sx={{
                    alignItems: "center",
                    borderBottom: 1,
                    borderColor: "divider",
                    display: "flex",
                    justifyContent: "space-between",
                    px: 4,
                    py: 3,
                  }}
                >
                  <Box>
                    <Typography component="h2" variant="h3">
                      Gelen Kutusu
                    </Typography>
                    <Typography color="text.secondary" variant="caption">
                      {visibleItems.length} teslimat
                    </Typography>
                  </Box>
                  <Checkbox
                    checked={selectedIds.size === visibleItems.length && visibleItems.length > 0}
                    indeterminate={selectedIds.size > 0 && selectedIds.size < visibleItems.length}
                    onChange={handleSelectAll}
                    size="small"
                  />
                </Box>
                <Box
                  aria-hidden="true"
                  sx={{
                    borderBottom: 1,
                    borderColor: "divider",
                    color: "text.secondary",
                    display: { xs: "none", md: "grid" },
                    fontSize: "caption.fontSize",
                    fontWeight: 700,
                    gap: 2,
                    gridTemplateColumns:
                      "auto minmax(180px, .8fr) minmax(140px, .5fr) minmax(140px, .5fr) minmax(150px, .6fr) auto",
                    px: 3,
                    py: 2,
                  }}
                >
                  <Box />
                  <Box>Bildirim / Kapsam</Box>
                  <Box>Durum</Box>
                  <Box>Deneme</Box>
                  <Box>Zaman</Box>
                  <Box>Aksiyon</Box>
                </Box>
                <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
                  {dateGroups.map((group) => (
                    <Box key={group.label}>
                      <Box
                        sx={{
                          bgcolor: "grey.50",
                          borderBottom: 1,
                          borderColor: "divider",
                          px: 4,
                          py: 1,
                        }}
                      >
                        <Typography color="text.secondary" sx={{ fontWeight: 700 }} variant="caption">
                          {group.label}
                        </Typography>
                      </Box>
                      {group.items.map((item) => (
                        <DeliveryRow
                          item={item}
                          key={item.deliveryId}
                          onMarkRead={onMarkRead}
                          onOpenDetail={setDrawerItem}
                          onSelect={handleSelect}
                          selected={selectedIds.has(item.deliveryId)}
                        />
                      ))}
                    </Box>
                  ))}
                </Box>

                {/* Load more */}
                {hasMore ? (
                  <Box sx={{ display: "flex", justifyContent: "center", p: 3 }}>
                    <Button
                      onClick={onLoadMore}
                      variant="outlined"
                    >
                      Daha fazla yükle
                    </Button>
                  </Box>
                ) : null}
              </Paper>
            )}
          </>
        ) : null}
      </Box>

      {/* Detail Drawer */}
      <DetailDrawer
        item={drawerItem}
        open={drawerItem !== null}
        onClose={() => setDrawerItem(null)}
      />
    </AppShell>
  );
}
