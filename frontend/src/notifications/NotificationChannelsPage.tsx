import {
  Alert,
  Box,
  Button,
  Chip,
  Paper,
  Typography,
} from "@mui/material";
import { Radio, RefreshCw, ShieldAlert } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { type StatusTone } from "../theme/tokens";
import type { NotificationChannel } from "./model";

export type NotificationChannelsPageState =
  | "normal"
  | "loading"
  | "empty"
  | "error"
  | "unauthorized";

interface NotificationChannelsPageProps {
  state?: NotificationChannelsPageState;
  channels?: NotificationChannel[];
  correlationId?: string;
  onRefresh?: () => void;
}

const channelTypeLabels: Record<string, string> = {
  IN_APP: "Uygulama içi",
  EMAIL: "E-posta",
  MESSAGING: "Mesajlaşma",
  SERVICENOW: "ServiceNow",
  JIRA: "Jira",
};

function channelStatusTone(status: string): StatusTone {
  return status === "ACTIVE" ? "success" : "warning";
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
    empty: ["Kanal kaydı bulunamadı", "Henüz bildirim kanalı tanımlanmamış."],
    error: [
      "Kanallar yüklenemedi",
      `Teknik bir sorun oluştu. Yeniden deneyin. İzleme kodu: ${correlationId ?? "bulunamadı"}.`,
    ],
    unauthorized: [
      "Bu görünüm için yetkiniz yok",
      "Kanal yönetimi platform yöneticisi rolü gerektirir.",
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

export function NotificationChannelsPage({
  state = "normal",
  channels = [],
  correlationId,
  onRefresh,
}: NotificationChannelsPageProps) {
  return (
    <AppShell currentPage="Bildirim Kanalları">
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
              Bildirim Kanalları
            </Typography>
            <Typography color="text.secondary">
              Teslimat kanalları ve yapılandırma durumu
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

        {state === "loading" ? (
          <Alert severity="info">
            <Typography sx={{ fontWeight: 700 }}>Kanallar yükleniyor…</Typography>
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
          channels.length === 0 ? (
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
                  gap: 2,
                  px: 4,
                  py: 3,
                }}
              >
                <Radio aria-hidden="true" size={18} />
                <Box>
                  <Typography component="h2" variant="h3">
                    Kanallar
                  </Typography>
                  <Typography color="text.secondary" variant="caption">
                    {channels.length} kanal
                  </Typography>
                </Box>
              </Box>
              <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
                {channels.map((channel) => (
                  <Box
                    component="li"
                    key={channel.channelId}
                    sx={{
                      alignItems: "center",
                      borderBottom: 1,
                      borderColor: "divider",
                      display: "flex",
                      gap: 3,
                      justifyContent: "space-between",
                      minHeight: 64,
                      px: 4,
                      py: 2.5,
                      "&:last-child": { borderBottom: 0 },
                    }}
                  >
                    <Box sx={{ minWidth: 0 }}>
                      <Box sx={{ alignItems: "center", display: "flex", gap: 1 }}>
                        <Typography sx={{ fontWeight: 600 }} variant="body2">
                          {channel.name}
                        </Typography>
                        <Chip
                          label={channelTypeLabels[channel.channelType] ?? channel.channelType}
                          size="small"
                          variant="outlined"
                        />
                      </Box>
                      <Typography color="text.secondary" variant="caption">
                        ID: {channel.channelId.slice(0, 12)}
                      </Typography>
                    </Box>
                    <Box sx={{ alignItems: "center", display: "flex", gap: 1.5 }}>
                      <StatusBadge
                        label={channel.status === "ACTIVE" ? "Aktif" : "Pasif"}
                        tone={channelStatusTone(channel.status)}
                      />
                      {channel.channelType !== "IN_APP" ? (
                        <ShieldAlert aria-hidden="true" color="gray" size={16} />
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
