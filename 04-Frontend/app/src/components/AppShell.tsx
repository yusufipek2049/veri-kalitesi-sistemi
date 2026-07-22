import type { ReactNode } from "react";
import { Box, Button, Chip, Divider, Typography } from "@mui/material";
import { designTokens } from "../theme/tokens";

const navigation = [
  { label: "Genel Bakış", glyph: "▦", active: true },
  { label: "Veri Kaynakları", glyph: "□" },
  { label: "Kurallar", glyph: "✓" },
  { label: "Çalıştırmalar", glyph: "▷" },
  { label: "Sorunlar", glyph: "!" },
  { label: "Raporlar", glyph: "▤" },
  { label: "Audit", glyph: "↗" },
];

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <Box
      sx={(theme) => ({
        display: "grid",
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
              height: 32,
              justifyContent: "center",
              width: 32,
            }}
          >
            VK
          </Box>
          <Typography sx={{ fontWeight: 800, whiteSpace: "nowrap", "@media (max-width: 1100px)": { display: "none" } }}>Veri Kalitesi</Typography>
        </Box>
        <Divider sx={{ borderColor: designTokens.color.nav.hover }} />
        <Box component="nav" aria-label="Ana navigasyon" sx={{ display: "grid", gap: 1, px: 3, py: 5 }}>
          {navigation.map((item) => (
            <Button
              key={item.label}
              aria-current={item.active ? "page" : undefined}
              aria-label={item.label}
              fullWidth
              sx={{
                bgcolor: item.active ? designTokens.color.nav.hover : "transparent",
                color: designTokens.color.nav.text,
                justifyContent: "flex-start",
                minHeight: 40,
                minWidth: 0,
                px: 3,
                position: "relative",
                "&::before": item.active ? {
                  bgcolor: "primary.main",
                  content: '""',
                  inset: 0,
                  position: "absolute",
                  width: (theme) => theme.spacing(1),
                } : undefined,
                "&:hover": { bgcolor: designTokens.color.nav.hover },
                "@media (max-width: 1100px)": { justifyContent: "center", px: 0 },
              }}
              variant="text"
            >
              <Box component="span" aria-hidden="true" sx={{ flex: "0 0 auto", width: 28 }}>{item.glyph}</Box>
              <Box component="span" sx={{ overflow: "hidden", textAlign: "left", whiteSpace: "nowrap", "@media (max-width: 1100px)": { display: "none" } }}>{item.label}</Box>
            </Button>
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
          <Typography color="text.secondary" variant="body2">Veri Kalitesi / <strong>Genel Bakış</strong></Typography>
          <Chip label="SENTETİK VERİ" size="small" color="primary" />
        </Box>
        <Box component="main" sx={{ minWidth: 0 }}>{children}</Box>
      </Box>
    </Box>
  );
}
