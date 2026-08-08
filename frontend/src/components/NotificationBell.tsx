import { useCallback, useEffect, useRef, useState } from "react";
import {
  Badge,
  Box,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Popover,
  Typography,
} from "@mui/material";
import { Bell, Inbox } from "lucide-react";
import { Link } from "react-router-dom";
import { fetchInbox, fetchUnreadCount } from "../notifications/api";
import type { NotificationDelivery } from "../notifications/model";

const eventTypeLabels: Record<string, string> = {
  QUALITY_THRESHOLD: "Kalite eşiği",
  CRITICAL_RULE_FAILURE: "Kritik kural hatası",
  TECHNICAL_ERROR: "Teknik hata",
  ISSUE_ASSIGNED: "Sorun ataması",
};

const statusLabels: Record<string, string> = {
  PENDING: "Bekliyor",
  SENDING: "Gönderiliyor",
  DELIVERED: "Teslim edildi",
  FAILED: "Başarısız",
  UNDELIVERABLE: "Teslim edilemez",
  REROUTED: "Yönlendirildi",
  READ: "Okundu",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function deliveryTitle(delivery: NotificationDelivery): string {
  return `Teslimat ${delivery.deliveryId.slice(0, 8)}`;
}

export function NotificationBell() {
  const [unreadCount, setUnreadCount] = useState(0);
  const [recentItems, setRecentItems] = useState<NotificationDelivery[]>([]);
  const [errorState, setErrorState] = useState<"idle" | "error" | "unauthorized">("idle");
  const [anchorEl, setAnchorEl] = useState<HTMLButtonElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

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

  useEffect(() => {
    void loadData();
    return () => {
      abortRef.current?.abort();
    };
  }, [loadData]);

  const handleOpen = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
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
                to="/notifications"
              >
                <ListItemText
                  primary={
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {eventTypeLabels[delivery.status] ?? statusLabels[delivery.status] ?? delivery.status}
                    </Typography>
                  }
                  secondary={
                    <Typography color="text.secondary" variant="caption">
                      {deliveryTitle(delivery)} · {formatDate(delivery.createdAt)}
                    </Typography>
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
    </>
  );
}
