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
  TextField,
  Typography,
} from "@mui/material";
import { RefreshCw, Route } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { NotificationTabs } from "./NotificationTabs";
import { StatusBadge } from "../components/StatusBadge";
import { type StatusTone } from "../theme/tokens";
import type { NotificationDelivery, NotificationDeliveryStatus } from "./model";

export type NotificationDeliveriesPageState =
  | "normal"
  | "loading"
  | "empty"
  | "error"
  | "unauthorized";

interface NotificationDeliveriesPageProps {
  state?: NotificationDeliveriesPageState;
  items?: NotificationDelivery[];
  correlationId?: string;
  onRefresh?: () => void;
  onReroute?: (deliveryId: string) => void;
}

interface DeliveryFilters {
  status: "ALL" | NotificationDeliveryStatus;
  recipientQuery: string;
}

const defaultFilters: DeliveryFilters = {
  status: "ALL",
  recipientQuery: "",
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
    empty: ["Teslimat kaydı bulunamadı", "Seçili filtrelerle eşleşen teslimat yok."],
    error: [
      "Teslimatlar yüklenemedi",
      `Teknik bir sorun oluştu. Yeniden deneyin. İzleme kodu: ${correlationId ?? "bulunamadı"}.`,
    ],
    unauthorized: [
      "Bu görünüm için yetkiniz yok",
      "Teslimat izleme operasyon veya platform yöneticisi rolü gerektirir.",
    ],
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

export function NotificationDeliveriesPage({
  state = "normal",
  items = [],
  correlationId,
  onRefresh,
  onReroute,
}: NotificationDeliveriesPageProps) {
  const [filters, setFilters] = useState<DeliveryFilters>(defaultFilters);

  const visibleItems = useMemo(
    () =>
      items.filter(
        (item) =>
          (filters.status === "ALL" || item.status === filters.status) &&
          (!filters.recipientQuery ||
            item.recipientUserId
              .toLocaleLowerCase("tr-TR")
              .includes(filters.recipientQuery.toLocaleLowerCase("tr-TR"))),
      ),
    [filters, items],
  );

  const resetFilters = () => setFilters(defaultFilters);

  return (
    <AppShell currentPage="Teslimat İzleme">
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
              Teslimat İzleme
            </Typography>
            <Typography color="text.secondary">
              Operasyon teslimat listesi, durum ve yeniden yönlendirme
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

        <NotificationTabs />

        {state !== "unauthorized" ? (
          <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
            <Box
              aria-label="Teslimat filtreleri"
              sx={{
                display: "grid",
                gap: 3,
                gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(180px, 1fr))" },
              }}
            >
              <FormControl>
                <InputLabel id="delivery-status-label">Durum</InputLabel>
                <Select
                  label="Durum"
                  labelId="delivery-status-label"
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      status: event.target.value as DeliveryFilters["status"],
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
              <TextField
                label="Alıcı"
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    recipientQuery: event.target.value,
                  }))
                }
                value={filters.recipientQuery}
              />
            </Box>
            <Box sx={{ display: "flex", gap: 2, justifyContent: "flex-end", mt: 3 }}>
              <Button onClick={resetFilters} size="small">
                Filtreleri temizle
              </Button>
            </Box>
          </Paper>
        ) : null}

        {state === "loading" ? (
          <Alert severity="info">
            <Typography sx={{ fontWeight: 700 }}>Teslimatlar yükleniyor…</Typography>
          </Alert>
        ) : null}

        {state === "empty" || state === "error" || state === "unauthorized" ? (
          <StateMessage
            correlationId={correlationId}
            onRefresh={onRefresh}
            state={state}
          />
        ) : null}

        {state === "normal" ? (
          visibleItems.length === 0 ? (
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
                    Teslimatlar
                  </Typography>
                  <Typography color="text.secondary" variant="caption">
                    {visibleItems.length} kayıt
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
                    "minmax(140px, .65fr) minmax(120px, .5fr) minmax(100px, .4fr) minmax(130px, .55fr) minmax(100px, .4fr) auto",
                  px: 4,
                  py: 2,
                }}
              >
                <Box>Teslimat</Box>
                <Box>Durum</Box>
                <Box>Deneme</Box>
                <Box>Zaman</Box>
                <Box>Alıcı</Box>
                <Box>Aksiyon</Box>
              </Box>
              <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
                {visibleItems.map((item) => (
                  <Box
                    component="li"
                    key={item.deliveryId}
                    sx={{
                      alignItems: "center",
                      borderBottom: 1,
                      borderColor: "divider",
                      display: "grid",
                      gap: 3,
                      gridTemplateColumns: {
                        xs: "minmax(0, 1fr) auto",
                        md: "minmax(140px, .65fr) minmax(120px, .5fr) minmax(100px, .4fr) minmax(130px, .55fr) minmax(100px, .4fr) auto",
                      },
                      minHeight: 64,
                      px: 4,
                      py: 2,
                      "&:last-child": { borderBottom: 0 },
                    }}
                  >
                    <Box sx={{ minWidth: 0 }}>
                      <Typography noWrap variant="body2" sx={{ fontWeight: 600 }}>
                        {item.deliveryId.slice(0, 12)}
                      </Typography>
                      <Typography color="text.secondary" noWrap variant="caption">
                        Olay {item.eventId.slice(0, 12)}
                      </Typography>
                    </Box>
                    <Box>
                      <StatusBadge
                        label={statusLabels[item.status] ?? item.status}
                        tone={statusTone(item.status)}
                      />
                    </Box>
                    <Box>
                      <Typography variant="caption">{item.attemptCount}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption">{formatDate(item.createdAt)}</Typography>
                      {item.deliveredAt ? (
                        <Typography color="text.secondary" variant="caption">
                          {" · "}{formatDate(item.deliveredAt)}
                        </Typography>
                      ) : null}
                    </Box>
                    <Box sx={{ minWidth: 0 }}>
                      <Typography noWrap variant="caption">
                        {item.recipientUserId.slice(0, 16)}
                      </Typography>
                    </Box>
                    <Box>
                      {item.status === "UNDELIVERABLE" ? (
                        <Button
                          onClick={() => onReroute?.(item.deliveryId)}
                          size="small"
                          startIcon={<Route aria-hidden="true" size={14} />}
                          variant="outlined"
                        >
                          Yönlendir
                        </Button>
                      ) : null}
                    </Box>
                  </Box>
                ))}
              </Box>
            </Paper>
          )
        ) : null}
      </Box>
    </AppShell>
  );
}
