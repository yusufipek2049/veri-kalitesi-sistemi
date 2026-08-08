import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Skeleton,
  Typography,
} from "@mui/material";
import {
  Bell,
  Check,
  Inbox as InboxIcon,
  RefreshCw,
} from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens, type StatusTone } from "../theme/tokens";
import type {
  NotificationDelivery,
  NotificationDeliveryStatus,
  NotificationEventType,
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
  correlationId?: string;
  onRefresh?: () => void;
  onMarkRead?: (deliveryId: string) => void;
  onFilterChange?: (filters: NotificationFilters) => void;
}

export interface NotificationFilters {
  status: "ALL" | NotificationDeliveryStatus;
  eventType: "ALL" | NotificationEventType;
}

const defaultFilters: NotificationFilters = {
  status: "ALL",
  eventType: "ALL",
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

function DeliveryRow({
  item,
  onMarkRead,
}: {
  item: NotificationDelivery;
  onMarkRead?: (id: string) => void;
}) {
  const tone = statusTone(item.status);
  const isRead = item.status === "READ";
  const canMarkRead = item.status === "DELIVERED";

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
          xs: "minmax(0, 1fr) auto",
          md: "minmax(160px, .7fr) minmax(140px, .5fr) minmax(120px, .45fr) minmax(150px, .6fr) auto",
        },
        minHeight: 72,
        px: 4,
        py: 2.5,
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Box sx={{ minWidth: 0 }}>
        <Typography noWrap sx={{ fontWeight: isRead ? 400 : 700 }} variant="body2">
          Teslimat {item.deliveryId.slice(0, 12)}
        </Typography>
        <Typography color="text.secondary" noWrap variant="caption">
          Olay {item.eventId.slice(0, 12)}
        </Typography>
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
      <Box>
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
  correlationId,
  onRefresh,
  onMarkRead,
  onFilterChange,
}: NotificationsPageProps) {
  const [filters, setFilters] = useState<NotificationFilters>(defaultFilters);

  const visibleItems = useMemo(
    () =>
      items.filter(
        (item) =>
          (filters.status === "ALL" || item.status === filters.status) &&
          (filters.eventType === "ALL" || true),
      ),
    [filters, items],
  );

  const applyFilters = () => onFilterChange?.(filters);
  const resetFilters = () => {
    setFilters(defaultFilters);
    onFilterChange?.(defaultFilters);
  };

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
          {state !== "unauthorized" ? (
            <Button
              onClick={onRefresh}
              startIcon={<RefreshCw aria-hidden="true" size={16} />}
              variant="contained"
            >
              Yenile
            </Button>
          ) : null}
        </Box>

        {state !== "unauthorized" ? (
          <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
            <Box
              aria-label="Bildirim filtreleri"
              sx={{
                display: "grid",
                gap: 3,
                gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(180px, 1fr))" },
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

        {state === "loading" ? (
          <Box aria-busy="true" aria-label="Bildirimler yükleniyor">
            {Array.from({ length: 5 }, (_, index) => (
              <Skeleton height={72} key={index} />
            ))}
          </Box>
        ) : null}

        {state === "empty" || state === "error" || state === "unauthorized" ? (
          <StateMessage
            correlationId={correlationId}
            onRefresh={onRefresh}
            state={state}
          />
        ) : null}

        {state === "normal" ? (
          <>
            <Box
              aria-label="Bildirim özeti"
              sx={{
                display: "grid",
                gap: 3,
                gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" },
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
                    gap: 3,
                    gridTemplateColumns:
                      "minmax(160px, .7fr) minmax(140px, .5fr) minmax(120px, .45fr) minmax(150px, .6fr) auto",
                    px: 4,
                    py: 2,
                  }}
                >
                  <Box>Teslimat</Box>
                  <Box>Durum</Box>
                  <Box>Deneme</Box>
                  <Box>Zaman</Box>
                  <Box>Aksiyon</Box>
                </Box>
                <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
                  {visibleItems.map((item) => (
                    <DeliveryRow item={item} key={item.deliveryId} onMarkRead={onMarkRead} />
                  ))}
                </Box>
              </Paper>
            )}
          </>
        ) : null}
      </Box>
    </AppShell>
  );
}
