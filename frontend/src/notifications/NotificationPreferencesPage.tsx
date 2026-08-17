import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Paper,
  Switch,
  Typography,
} from "@mui/material";
import { Lock, RefreshCw, Settings2 } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { NotificationTabs } from "./NotificationTabs";
import type { NotificationSubscription } from "./model";

export type NotificationPreferencesPageState =
  | "normal"
  | "loading"
  | "empty"
  | "error"
  | "unauthorized";

interface NotificationPreferencesPageProps {
  state?: NotificationPreferencesPageState;
  subscriptions?: NotificationSubscription[];
  correlationId?: string;
  onRefresh?: () => void;
  onToggleSubscription?: (subscriptionId: string, active: boolean) => void;
}

const eventTypeLabels: Record<string, string> = {
  QUALITY_THRESHOLD: "Kalite eşiği",
  CRITICAL_RULE_FAILURE: "Kritik kural hatası",
  TECHNICAL_ERROR: "Teknik hata",
  ISSUE_ASSIGNED: "Sorun ataması",
};

const mandatoryEventTypes = new Set(["ISSUE_ASSIGNED"]);

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
    empty: ["Tercih kaydı bulunamadı", "Henüz bildirim tercihi tanımlanmamış."],
    error: [
      "Tercihler yüklenemedi",
      `Teknik bir sorun oluştu. Yeniden deneyin. İzleme kodu: ${correlationId ?? "bulunamadı"}.`,
    ],
    unauthorized: [
      "Bu görünüm için yetkiniz yok",
      "Bildirim tercihleriniz gösterilmedi.",
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

export function NotificationPreferencesPage({
  state = "normal",
  subscriptions = [],
  correlationId,
  onRefresh,
  onToggleSubscription,
}: NotificationPreferencesPageProps) {
  const [toggledIds, setToggledIds] = useState<Set<string>>(new Set());

  const handleToggle = (subscriptionId: string, currentlyActive: boolean) => {
    setToggledIds((prev) => {
      const next = new Set(prev);
      if (currentlyActive) next.add(subscriptionId);
      else next.delete(subscriptionId);
      return next;
    });
    onToggleSubscription?.(subscriptionId, !currentlyActive);
  };

  return (
    <AppShell currentPage="Bildirim Tercihleri">
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
              Bildirim Tercihleri
            </Typography>
            <Typography color="text.secondary">
              Olay türü ve kanal bazlı bildirim tercihlerinizi yönetin
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

        {state === "loading" ? (
          <Alert severity="info">
            <Typography sx={{ fontWeight: 700 }}>Tercihler yükleniyor…</Typography>
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
          subscriptions.length === 0 ? (
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
                <Settings2 aria-hidden="true" size={18} />
                <Box>
                  <Typography component="h2" variant="h3">
                    Tercihler
                  </Typography>
                  <Typography color="text.secondary" variant="caption">
                    {subscriptions.length} tercih
                  </Typography>
                </Box>
              </Box>
              <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
                {subscriptions.map((sub) => {
                  const isMandatory = mandatoryEventTypes.has(sub.eventType);
                  const isToggled = toggledIds.has(sub.subscriptionId);
                  const effectiveActive = isMandatory ? true : sub.status === "ACTIVE";

                  return (
                    <Box
                      component="li"
                      key={sub.subscriptionId}
                      sx={{
                        alignItems: "center",
                        borderBottom: 1,
                        borderColor: "divider",
                        display: "flex",
                        gap: 3,
                        justifyContent: "space-between",
                        minHeight: 64,
                        px: 4,
                        py: 2,
                        "&:last-child": { borderBottom: 0 },
                      }}
                    >
                      <Box sx={{ minWidth: 0 }}>
                        <Box sx={{ alignItems: "center", display: "flex", gap: 1 }}>
                          <Typography sx={{ fontWeight: 600 }} variant="body2">
                            {eventTypeLabels[sub.eventType] ?? sub.eventType}
                          </Typography>
                          {isMandatory ? (
                            <Chip
                              icon={<Lock aria-hidden="true" size={12} />}
                              label="Zorunlu"
                              size="small"
                              sx={{ fontWeight: 600 }}
                            />
                          ) : null}
                        </Box>
                        <Typography color="text.secondary" variant="caption">
                          Kapsam: {sub.scopeType ? `${sub.scopeType}/${sub.scopeId}` : "Tümü"}
                          {" · Kanal "}
                          {sub.channelId.slice(0, 8)}
                        </Typography>
                      </Box>
                      <Switch
                        aria-label={`${eventTypeLabels[sub.eventType] ?? sub.eventType} bildirimi ${effectiveActive ? "kapat" : "aç"}`}
                        checked={effectiveActive}
                        disabled={isMandatory || isToggled}
                        onChange={() => handleToggle(sub.subscriptionId, effectiveActive)}
                      />
                    </Box>
                  );
                })}
              </Box>
            </Paper>
          )
        ) : null}
      </Box>
    </AppShell>
  );
}
