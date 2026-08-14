import { useCallback, useEffect, useRef, useState } from "react";
import {
  Alert,
  Badge,
  Box,
  Button,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Popover,
  Snackbar,
  Typography,
} from "@mui/material";
import { Bell, Inbox } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { fetchInbox, fetchUnreadCount } from "../notifications/api";
import type { NotificationDelivery } from "../notifications/model";
import { useNotificationStream } from "../notifications/useNotificationStream";

const POLL_INTERVAL_MS = 30_000;

const eventTypeLabels: Record<string, string> = {
  QUALITY_THRESHOLD: "Kalite eşiği",
  CRITICAL_RULE_FAILURE: "Kritik kural hatası",
  TECHNICAL_ERROR: "Teknik hata",
  ISSUE_ASSIGNED: "Sorun ataması",
  RULE_APPROVAL_REQUESTED: "Kural onay talebi",
  RULE_APPROVAL_DECIDED: "Onay kararı",
  RULE_APPROVAL_WITHDRAWN: "Onay geri çekme",
  RULE_APPROVAL_EXPIRED: "Onay süresi doldu",
};

const scopeTypeLabels: Record<string, string> = {
  DATASET: "Dataset",
  SOURCE: "Veri kaynağı",
  RULE: "Kural",
  EXECUTION: "Çalıştırma",
  ISSUE_ASSIGNMENT: "Sorun ataması",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function deliveryTitle(delivery: NotificationDelivery): string {
  if (delivery.eventType) {
    return eventTypeLabels[delivery.eventType] ?? delivery.eventType;
  }
  return `Teslimat ${delivery.deliveryId.slice(0, 8)}`;
}

function deliveryScopeLabel(delivery: NotificationDelivery): string | null {
  if (!delivery.scopeType || !delivery.scopeId) return null;
  const typeLabel = scopeTypeLabels[delivery.scopeType] ?? delivery.scopeType;
  const shortId = delivery.scopeId.length > 20
    ? `${delivery.scopeId.slice(0, 18)}…`
    : delivery.scopeId;
  return `${typeLabel}: ${shortId}`;
}

function deliveryLinkTarget(delivery: NotificationDelivery): string {
  if (delivery.scopeType === "DATASET" && delivery.scopeId) {
    return `/catalog/datasets/${delivery.scopeId}`;
  }
  if (delivery.scopeType === "SOURCE") {
    return "/data-sources";
  }
  if (delivery.scopeType === "RULE") {
    return "/rules";
  }
  return "/notifications";
}

export function NotificationBell() {
  const navigate = useNavigate();
  const [unreadCount, setUnreadCount] = useState(0);
  const [recentItems, setRecentItems] = useState<NotificationDelivery[]>([]);
  const [errorState, setErrorState] = useState<"idle" | "error" | "unauthorized">("idle");
  const [anchorEl, setAnchorEl] = useState<HTMLButtonElement | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const sseConnectedRef = useRef(false);

  const loadData = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const [count, inbox] = await Promise.all([
        fetchUnreadCount(),
        fetchInbox({ limit: 5 }),
      ]);
      if (controller.signal.aborted) return;
      setUnreadCount(count);
      setRecentItems(inbox.deliveries);
      setErrorState("idle");
    } catch (error: unknown) {
      if (controller.signal.aborted) return;
      if (
        error instanceof Error &&
        ("kind" in error && (error as { kind: string }).kind === "unauthorized")
      ) {
        setErrorState("unauthorized");
      } else {
        setErrorState("error");
      }
    }
  }, []);

  // SSE integration — replaces polling when connected
  const handleNewDelivery = useCallback((payload: Record<string, unknown>) => {
    setUnreadCount((c) => c + 1);
    const eventType = payload.event_type as string | undefined;
    const label = eventType ? (eventTypeLabels[eventType] ?? eventType) : "Yeni bildirim";
    setToastMessage(label);
    // Refresh inbox to keep the popover list current
    void loadData();
  }, [loadData]);

  const { connected: sseConnected } = useNotificationStream({
    enabled: errorState !== "unauthorized",
    onNewDelivery: handleNewDelivery,
  });

  // Track SSE connection state for fallback logic
  useEffect(() => {
    sseConnectedRef.current = sseConnected;
  }, [sseConnected]);

  // Polling fallback — only active when SSE is not connected
  useEffect(() => {
    void loadData();

    // Start polling only when SSE is not connected
    if (sseConnected) return;

    const intervalId = setInterval(() => {
      if (!sseConnectedRef.current) {
        void loadData();
      }
    }, POLL_INTERVAL_MS);

    return () => {
      abortRef.current?.abort();
      clearInterval(intervalId);
    };
  }, [loadData, sseConnected]);

  const handleOpen = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleToastClose = () => {
    setToastMessage(null);
  };

  const handleToastNavigate = () => {
    setToastMessage(null);
    navigate("/notifications");
  };

  const open = Boolean(anchorEl);
  const showBadge = errorState === "idle" && unreadCount > 0;

  return (
    <>
      <Badge
        badgeContent={showBadge ? Math.min(unreadCount, 99) : 0}
        color="error"
        invisible={!showBadge}
        max={99}
      >
        <IconButton
          aria-label={
            errorState === "unauthorized"
              ? "Bildirimler — yetkisiz"
              : errorState === "error"
                ? "Bildirimler — yüklenemedi"
                : `Bildirimler — ${unreadCount} okunmamış`
          }
          color="inherit"
          onClick={handleOpen}
          size="small"
        >
          <Bell aria-hidden="true" size={18} />
        </IconButton>
      </Badge>
      <Popover
        anchorEl={anchorEl}
        anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
        onClose={handleClose}
        open={open}
        transformOrigin={{ horizontal: "right", vertical: "top" }}
        slotProps={{
          paper: {
            sx: { mt: 1, minWidth: 320, maxWidth: 400 },
          },
        }}
      >
        <Box sx={{ px: 3, py: 2 }}>
          <Typography sx={{ fontWeight: 700 }} variant="body2">
            Bildirimler
          </Typography>
        </Box>
        {errorState === "unauthorized" ? (
          <Box sx={{ px: 3, pb: 2 }}>
            <Typography color="text.secondary" variant="caption">
              Bildirimleri görüntüleme yetkiniz yok.
            </Typography>
          </Box>
        ) : errorState === "error" ? (
          <Box sx={{ px: 3, pb: 2 }}>
            <Typography color="text.secondary" variant="caption">
              Bildirimler yüklenemedi.
            </Typography>
          </Box>
        ) : recentItems.length === 0 ? (
          <Box sx={{ px: 3, pb: 2, textAlign: "center" }}>
            <Inbox aria-hidden="true" size={24} />
            <Typography color="text.secondary" sx={{ mt: 1 }} variant="caption">
              Yeni bildirim yok.
            </Typography>
          </Box>
        ) : (
          <List disablePadding>
            {recentItems.map((delivery) => (
              <ListItemButton
                component={Link}
                key={delivery.deliveryId}
                onClick={handleClose}
                to={deliveryLinkTarget(delivery)}
              >
                <ListItemText
                  primary={
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {deliveryTitle(delivery)}
                    </Typography>
                  }
                  secondary={
                    <>
                      {deliveryScopeLabel(delivery) ? (
                        <Typography color="text.secondary" sx={{ display: "block" }} variant="caption">
                          {deliveryScopeLabel(delivery)}
                        </Typography>
                      ) : null}
                      <Typography color="text.secondary" variant="caption">
                        {formatDate(delivery.createdAt)}
                      </Typography>
                    </>
                  }
                />
              </ListItemButton>
            ))}
          </List>
        )}
        <Box sx={{ borderTop: 1, borderColor: "divider", px: 3, py: 1.5 }}>
          <Typography
            component={Link}
            onClick={handleClose}
            sx={{ color: "primary.main", fontWeight: 600, textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
            to="/notifications"
            variant="caption"
          >
            Tümünü görüntüle
          </Typography>
        </Box>
      </Popover>

      {/* New notification toast */}
      <Snackbar
        anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
        autoHideDuration={5000}
        message={toastMessage ? `Yeni bildirim: ${toastMessage}` : ""}
        onClose={handleToastClose}
        open={toastMessage !== null}
      >
        <Alert
          action={
            <Button color="inherit" onClick={handleToastNavigate} size="small">
              Görüntüle
            </Button>
          }
          onClose={handleToastClose}
          severity="info"
          sx={{ width: "100%" }}
        >
          {toastMessage ? `Yeni bildirim: ${toastMessage}` : ""}
        </Alert>
      </Snackbar>
    </>
  );
}
