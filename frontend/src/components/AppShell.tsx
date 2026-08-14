import type { ReactNode } from "react";
import { useState } from "react";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  AlertCircle,
  BarChart3,
  Bell,
  Database,
  LayoutDashboard,
  Library,
  ListChecks,
  Moon,
  PlayCircle,
  Power,
  ScrollText,
  Sun,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router-dom";
import { designTokens } from "../theme/tokens";
import { useThemeMode } from "../theme/ThemeModeProvider";
import { NotificationBell } from "./NotificationBell";
import { useLauncherControl } from "../launcherControl";

interface NavigationItem {
  label: string;
  icon: LucideIcon;
  href: string;
}

const navigationGroups: Array<{ label: string; items: NavigationItem[] }> = [
  {
    label: "ANALİZ",
    items: [
      { label: "Genel Bakış", icon: LayoutDashboard, href: "/dashboard" },
      { label: "Veri Kaynakları", icon: Database, href: "/data-sources" },
      { label: "Katalog", icon: Library, href: "/catalog" },
      { label: "Kurallar", icon: ListChecks, href: "/rules" },
      { label: "Çalıştırmalar", icon: PlayCircle, href: "/executions" },
      { label: "Skorlar", icon: BarChart3, href: "/scores" },
    ],
  },
  {
    label: "OPERASYON",
    items: [
      { label: "Sorunlar", icon: AlertCircle, href: "/issues" },
      { label: "Bildirimler", icon: Bell, href: "/notifications" },
      { label: "Denetim", icon: ScrollText, href: "/audit" },
    ],
  },
];

interface AppShellProps {
  children: ReactNode;
  currentPage?: string;
}

export function AppShell({ children, currentPage = "Genel Bakış" }: AppShellProps) {
  const { mode, toggleMode } = useThemeMode();
  const { available, cancelError, requestShutdown, status: shutdownStatus } = useLauncherControl();
  const [confirmationOpen, setConfirmationOpen] = useState(false);
  const themeActionLabel = mode === "light" ? "Koyu temaya geç" : "Açık temaya geç";
  const shutdownPending = shutdownStatus === "requesting";

  if (shutdownStatus === "closing" || shutdownStatus === "closed") {
    return (
      <Box
        aria-live="polite"
        sx={{
          alignItems: "center",
          bgcolor: "background.default",
          display: "flex",
          justifyContent: "center",
          minHeight: "100vh",
          p: 6,
          textAlign: "center",
        }}
      >
        <Box>
          <Power aria-hidden="true" color={designTokens.color.nav.background} size={32} />
          <Typography component="h1" sx={{ fontWeight: 800, mt: 3 }} variant="h5">
            {shutdownStatus === "closing"
              ? "Uygulama kapatılıyor…"
              : "Uygulama kapatıldı. Bu sekmeyi kapatabilirsiniz."}
          </Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Box
      sx={(theme) => ({
        display: "grid",
        color: "text.primary",
        gridTemplateColumns: `${theme.appLayout.navExpanded}px minmax(0, 1fr)`,
        minHeight: "100vh",
        "@media (max-width: 1100px)": {
          gridTemplateColumns: `${theme.appLayout.navCompact}px minmax(0, 1fr)`,
        },
      })}
    >
      <Box
        component="aside"
        sx={{
          bgcolor: designTokens.color.nav.background,
          color: designTokens.color.nav.text,
          display: "flex",
          flexDirection: "column",
          minHeight: "100vh",
          overflow: "hidden",
        }}
      >
        <Box sx={{ alignItems: "center", display: "flex", gap: 3, minHeight: (theme) => theme.appLayout.topBarHeight, px: 4 }}>
          <Box
            aria-hidden="true"
            sx={{
              alignItems: "center",
              bgcolor: "primary.main",
              borderRadius: 1,
              color: "primary.contrastText",
              display: "flex",
              flex: "0 0 auto",
              fontWeight: 800,
              height: (theme) => theme.appLayout.brandMarkSize,
              justifyContent: "center",
              width: (theme) => theme.appLayout.brandMarkSize,
            }}
          >
            VK
          </Box>
          <Typography sx={{ fontWeight: 800, whiteSpace: "nowrap", "@media (max-width: 1100px)": { display: "none" } }}>Veri Kalitesi</Typography>
        </Box>
        <Divider sx={{ borderColor: designTokens.color.nav.hover }} />
        <Box component="nav" aria-label="Ana navigasyon" sx={{ display: "grid", gap: 5, px: 3, py: 5 }}>
          {navigationGroups.map((group) => (
            <Box component="section" key={group.label} aria-labelledby={`nav-group-${group.label.toLocaleLowerCase("tr-TR")}`}>
              <Typography
                id={`nav-group-${group.label.toLocaleLowerCase("tr-TR")}`}
                component="h2"
                sx={{ color: designTokens.color.nav.muted, display: "block", mb: 2, px: 3, "@media (max-width: 1100px)": { display: "none" } }}
                variant="caption"
              >
                {group.label}
              </Typography>
              <Box sx={{ display: "grid", gap: 1 }}>
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const active = item.label === currentPage;
                  return (
                    <Tooltip key={item.label} placement="right" title={item.label}>
                      <Button
                        aria-current={active ? "page" : undefined}
                        aria-label={item.label}
                        component={Link}
                        to={item.href}
                        fullWidth
                        sx={(theme) => ({
                          bgcolor: active ? designTokens.color.nav.hover : "transparent",
                          color: designTokens.color.nav.text,
                          justifyContent: "flex-start",
                          minHeight: theme.appLayout.navItemHeight,
                          minWidth: 0,
                          px: 3,
                          position: "relative",
                          "&::before": active ? {
                            bgcolor: "primary.main",
                            content: '""',
                            inset: 0,
                            position: "absolute",
                            width: theme.spacing(1),
                          } : undefined,
                          "&:hover": { bgcolor: designTokens.color.nav.hover },
                          "@media (max-width: 1100px)": { justifyContent: "center", px: 0 },
                        })}
                        variant="text"
                      >
                        <Box
                          component="span"
                          data-testid="navigation-icon-slot"
                          aria-hidden="true"
                          sx={(theme) => ({
                            alignItems: "center",
                            display: "inline-flex",
                            flex: "0 0 auto",
                            height: theme.appLayout.navIconSlot,
                            justifyContent: "center",
                            width: theme.appLayout.navIconSlot,
                          })}
                        >
                          <Icon size={designTokens.layout.navIconSize} strokeWidth={1.8} />
                        </Box>
                        <Box component="span" sx={{ ml: 2, overflow: "hidden", textAlign: "left", whiteSpace: "nowrap", "@media (max-width: 1100px)": { display: "none" } }}>{item.label}</Box>
                      </Button>
                    </Tooltip>
                  );
                })}
              </Box>
            </Box>
          ))}
        </Box>
        <Box sx={{ mt: "auto", p: 4, "@media (max-width: 1100px)": { px: 2 } }}>
          <Divider sx={{ borderColor: designTokens.color.nav.hover, mb: 4 }} />
          <Typography sx={{ fontWeight: 700, "@media (max-width: 1100px)": { display: "none" } }} variant="body2">Demo Kullanıcı</Typography>
          <Typography sx={{ color: designTokens.color.nav.muted, "@media (max-width: 1100px)": { display: "none" } }} variant="caption">Sentetik görünüm</Typography>
        </Box>
      </Box>

      <Box sx={{ minWidth: 0 }}>
        <Box
          component="header"
          sx={(theme) => ({
            alignItems: "center",
            bgcolor: "background.paper",
            borderBottom: 1,
            borderColor: "divider",
            display: "flex",
            justifyContent: "space-between",
            minHeight: theme.appLayout.topBarHeight,
            px: { md: 4, lg: 6 },
          })}
        >
          <Typography color="text.secondary" variant="body2">Veri Kalitesi / <strong>{currentPage}</strong></Typography>
          <Stack direction="row" sx={{ alignItems: "center", gap: 2 }}>
            <Tooltip
              title={available ? "Uygulama servislerini güvenli biçimde durdur" : "Yalnız masaüstü başlatıcısıyla açıldığında kullanılabilir."}
            >
              <span>
                <Button
                  disabled={!available || shutdownPending}
                  onClick={() => setConfirmationOpen(true)}
                  size="small"
                  startIcon={<Power aria-hidden="true" size={designTokens.layout.navIconSize} />}
                  sx={{
                    "&.Mui-focusVisible": {
                      outline: `2px solid ${designTokens.color.brand.primary}`,
                      outlineOffset: 2,
                    },
                  }}
                  variant="outlined"
                >
                  Kapat
                </Button>
              </span>
            </Tooltip>
            <NotificationBell />
            <Tooltip title={themeActionLabel}>
              <IconButton aria-label={themeActionLabel} color="inherit" onClick={toggleMode} size="small">
                {mode === "light" ? <Moon aria-hidden="true" size={designTokens.layout.navIconSize} /> : <Sun aria-hidden="true" size={designTokens.layout.navIconSize} />}
              </IconButton>
            </Tooltip>
          </Stack>
        </Box>
        <Box component="main" sx={{ minWidth: 0 }}>{children}</Box>
      </Box>

      <Dialog
        aria-describedby="launcher-shutdown-description"
        aria-labelledby="launcher-shutdown-title"
        fullWidth
        maxWidth="xs"
        onClose={() => setConfirmationOpen(false)}
        open={confirmationOpen}
      >
        <DialogTitle id="launcher-shutdown-title">Veri Kalitesi Sistemi kapatılsın mı?</DialogTitle>
        <DialogContent>
          <DialogContentText id="launcher-shutdown-description">
            Uygulama servisleri durdurulacak. Veritabanı verileri silinmeyecektir.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmationOpen(false)}>Vazgeç</Button>
          <Button
            autoFocus
            disabled={shutdownPending}
            onClick={() => {
              setConfirmationOpen(false);
              void requestShutdown();
            }}
            variant="contained"
          >
            Uygulamayı kapat
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        aria-describedby="launcher-shutdown-error-description"
        aria-labelledby="launcher-shutdown-error-title"
        fullWidth
        maxWidth="xs"
        onClose={cancelError}
        open={shutdownStatus === "error"}
      >
        <DialogTitle id="launcher-shutdown-error-title" sx={{ color: designTokens.color.status.technical }}>
          Teknik hata
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="launcher-shutdown-error-description">
            Uygulama servislerinin durdurulması başlatılamadı. Servisler çalışıyor olabilir.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={cancelError}>Vazgeç</Button>
          <Button onClick={() => void requestShutdown()} variant="contained">Tekrar dene</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
