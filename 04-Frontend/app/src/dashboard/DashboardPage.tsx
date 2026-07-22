import {
  Alert,
  Box,
  Button,
  Paper,
  Skeleton,
  Stack,
  Typography,
} from "@mui/material";
import { AlertFeed } from "../components/AlertFeed";
import { AppShell } from "../components/AppShell";
import { KpiCard } from "../components/KpiCard";
import { TrendPanel } from "../components/TrendPanel";
import {
  alerts,
  kpis,
  longContentKpis,
  trendObservations,
  type DashboardState,
} from "./model";

interface DashboardPageProps {
  state?: DashboardState;
}

function LoadingDashboard() {
  return (
    <Box aria-label="Dashboard yükleniyor" aria-busy="true">
      <Box sx={{ display: "grid", gap: 4, gridTemplateColumns: { md: "repeat(2, minmax(0, 1fr))", lg: "repeat(4, minmax(0, 1fr))" } }}>
        {kpis.map((item) => <Skeleton key={item.id} height={132} variant="rounded" />)}
      </Box>
      <Skeleton height={360} sx={{ mt: 5 }} variant="rounded" />
    </Box>
  );
}

function StateMessage({ state }: { state: "empty" | "error" | "unauthorized" }) {
  const content = {
    empty: {
      severity: "info" as const,
      title: "Veri bulunamadı",
      body: "Son 30 gün ve seçili kapsam için hesaplanmış bir sonuç yok. Skor yerine sıfır gösterilmedi.",
      action: "Filtreleri temizle",
    },
    error: {
      severity: "error" as const,
      title: "Dashboard yüklenemedi",
      body: "Teknik bir sorun oluştu. Tarih aralığını daraltıp yeniden deneyin. İzleme kodu: SYN-7F21.",
      action: "Yeniden dene",
    },
    unauthorized: {
      severity: "warning" as const,
      title: "Bu görünüm için yetkiniz yok",
      body: "İstenen kapsamın içeriği gösterilmedi. Erişim talebi için yetkili biriminizle iletişime geçin.",
      action: "Genel bakışa dön",
    },
  }[state];

  const isTechnicalError = state === "error";

  return (
    <Alert
      action={<Button color="inherit" size="small">{content.action}</Button>}
      severity={content.severity}
      sx={(theme) => ({
        alignItems: "center",
        ...(isTechnicalError
          ? {
              bgcolor: theme.status.technicalSurface,
              color: theme.status.technical,
              "& .MuiAlert-icon": { color: theme.status.technical },
            }
          : {}),
      })}
    >
      <Typography sx={{ fontWeight: 700 }}>{content.title}</Typography>
      <Typography variant="body2">{content.body}</Typography>
    </Alert>
  );
}

export function DashboardPage({ state = "normal" }: DashboardPageProps) {
  const visibleKpis = state === "long-content" ? longContentKpis : kpis;

  return (
    <AppShell>
      <Box
        sx={(theme) => ({
          display: "grid",
          gap: 5,
          margin: "0 auto",
          maxWidth: theme.appLayout.contentMaxWidth,
          p: { md: 4, lg: 6 },
          width: "100%",
        })}
      >
        <Box sx={{ alignItems: { md: "center" }, display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 4, justifyContent: "space-between" }}>
          <Box>
            <Typography component="h1" variant="h1">Genel Bakış</Typography>
            <Typography color="text.secondary">Yetkili kapsam için son 30 günlük veri kalitesi görünümü</Typography>
          </Box>
          <Stack direction="row" sx={{ flexWrap: "wrap", gap: 2 }}>
            <Button variant="outlined">Tüm veri alanları</Button>
            <Button variant="outlined">Son 30 gün</Button>
            <Button variant="contained">Yenile</Button>
          </Stack>
        </Box>

        <Alert severity="info" sx={{ py: 1 }}>
          Bu ekran yalnız sentetik gösterim verisi kullanır; üretim API'si, kullanıcı oturumu veya banka verisi bağlı değildir.
        </Alert>

        {state === "loading" ? <LoadingDashboard /> : null}
        {state === "empty" || state === "error" || state === "unauthorized" ? <StateMessage state={state} /> : null}

        {state === "normal" || state === "long-content" ? (
          <>
            <Box component="section" aria-label="Özet göstergeler" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))", lg: "repeat(4, minmax(0, 1fr))" } }}>
              {visibleKpis.map((item) => <KpiCard item={item} key={item.id} />)}
            </Box>
            <Box sx={{ display: "grid", gap: 4, gridTemplateColumns: { xs: "minmax(0, 1fr)", lg: "minmax(0, 2fr) minmax(320px, 1fr)" } }}>
              <TrendPanel observations={trendObservations} />
              <AlertFeed items={alerts} />
            </Box>
            <Paper component="section" variant="outlined" sx={{ borderRadius: 1.5, p: 4 }}>
              <Typography component="h2" variant="h3">Ölçüm Notu</Typography>
              <Typography color="text.secondary" sx={{ mt: 2 }} variant="body2">
                Son sonuç sınırlı kapsama rağmen onaylı sentetik politika koşullarını karşılıyor. Provizyonel 13 Temmuz sonucu resmî trend ve SLA hesabına katılmadı; önceki resmî skor geçersiz kılınmadı.
              </Typography>
            </Paper>
          </>
        ) : null}
      </Box>
    </AppShell>
  );
}
