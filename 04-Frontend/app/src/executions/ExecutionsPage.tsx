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
  Skeleton,
  TextField,
  Typography,
} from "@mui/material";
import {
  Ban,
  CheckCircle2,
  CircleDashed,
  Clock3,
  PlayCircle,
  RefreshCw,
  Search,
  TimerOff,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens, type StatusTone } from "../theme/tokens";
import {
  syntheticExecutions,
  type ExecutionListItem,
  type ExecutionState,
} from "./model";

interface ExecutionsPageProps {
  state?: ExecutionState;
  items?: ExecutionListItem[];
  correlationId?: string;
  onRefresh?: () => void;
}

const statusLabels: Record<string, string> = {
  QUEUED: "Kuyrukta",
  RUNNING: "Çalışıyor",
  CANCEL_REQUESTED: "İptal bekliyor",
  SUCCESS: "Tamamlandı",
  PARTIAL: "Kısmi",
  TECHNICAL_ERROR: "Teknik hata",
  TIMEOUT: "Zaman aşımı",
  CANCELLED: "İptal edildi",
};

const typeLabels: Record<string, string> = {
  MANUAL: "Manuel",
  SCHEDULED: "Zamanlanmış",
};

const errorLabels: Record<string, string> = {
  CONNECTION_UNAVAILABLE: "Bağlantı kullanılamıyor",
  QUERY_TIMEOUT: "Sorgu zaman aşımı",
  TOTAL_TIMEOUT: "Toplam süre aşıldı",
};

function executionPresentation(status: string): { icon: LucideIcon; tone: StatusTone } {
  if (status === "SUCCESS") return { icon: CheckCircle2, tone: "success" };
  if (status === "RUNNING") return { icon: PlayCircle, tone: "info" };
  if (status === "PARTIAL") return { icon: CircleDashed, tone: "warning" };
  if (status === "TECHNICAL_ERROR") return { icon: Wrench, tone: "technical" };
  if (status === "TIMEOUT") return { icon: TimerOff, tone: "technical" };
  if (status === "CANCEL_REQUESTED") return { icon: Ban, tone: "warning" };
  if (status === "CANCELLED") return { icon: Ban, tone: "unknown" };
  return { icon: Clock3, tone: "unknown" };
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function durationLabel(item: ExecutionListItem): string {
  if (!item.startedAt) return "Henüz başlamadı";
  if (!item.finishedAt) return "Devam ediyor";
  const seconds = Math.max(
    0,
    Math.round((new Date(item.finishedAt).getTime() - new Date(item.startedAt).getTime()) / 1000),
  );
  if (seconds >= 3600) return `${Math.floor(seconds / 3600)} sa ${Math.round((seconds % 3600) / 60)} dk`;
  if (seconds >= 60) return `${Math.floor(seconds / 60)} dk`;
  return `${seconds} sn`;
}

function ExecutionRow({ item }: { item: ExecutionListItem }) {
  const presentation = executionPresentation(item.status);
  const Icon = presentation.icon;
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
          xs: "40px minmax(0, 1fr)",
          md: "40px minmax(230px, 1fr) minmax(145px, .65fr) minmax(150px, .65fr)",
          lg: "40px minmax(240px, 1.2fr) minmax(145px, .65fr) minmax(130px, .55fr) minmax(155px, .7fr) minmax(180px, .8fr)",
        },
        minHeight: 84,
        px: 4,
        py: 3,
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Box
        aria-hidden="true"
        data-testid="execution-icon-slot"
        sx={(theme) => ({
          alignItems: "center",
          bgcolor: theme.status[`${presentation.tone}Surface`],
          borderRadius: 1,
          color: theme.status[presentation.tone],
          display: "flex",
          height: 40,
          justifyContent: "center",
          width: 40,
        })}
      >
        <Icon size={designTokens.layout.navIconSize} strokeWidth={1.8} />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography noWrap sx={{ fontWeight: 700 }}>{item.id}</Typography>
        <Typography color="text.secondary" variant="caption">
          {typeLabels[item.executionType] ?? item.executionType} · {item.ruleCount} kural · {item.sourceCount} kaynak
        </Typography>
      </Box>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" } }}>
        <StatusBadge
          label={statusLabels[item.status] ?? item.status}
          tone={presentation.tone}
        />
      </Box>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" } }}>
        <Typography variant="body2">{item.workloadClass === "HEAVY" ? "Yoğun iş" : "Hafif iş"}</Typography>
        <Typography color="text.secondary" variant="caption">{item.attemptCount} deneme</Typography>
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" } }}>
        <Typography variant="body2">{formatDate(item.createdAt)}</Typography>
        <Typography color="text.secondary" variant="caption">{durationLabel(item)}</Typography>
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" }, minWidth: 0 }}>
        <Typography noWrap variant="body2">
          {item.errorClass ? errorLabels[item.errorClass] ?? item.errorClass : "Teknik hata yok"}
        </Typography>
        <Typography color="text.secondary" variant="caption">
          {item.finishedAt ? `Bitiş: ${formatDate(item.finishedAt)}` : "Henüz kapanmadı"}
        </Typography>
      </Box>
    </Box>
  );
}

function StateMessage({
  state,
  correlationId,
  onRefresh,
}: Pick<ExecutionsPageProps, "correlationId" | "onRefresh"> & {
  state: "empty" | "error" | "unauthorized";
}) {
  const content = {
    empty: ["Çalıştırma bulunamadı", "Yetkili kapsam ve seçili filtrelerle eşleşen çalıştırma yok."],
    error: ["Çalıştırmalar yüklenemedi", `Teknik bir sorun oluştu. Yeniden deneyin. İzleme kodu: ${correlationId ?? "bulunamadı"}.`],
    unauthorized: ["Bu görünüm için yetkiniz yok", "Çalıştırma geçmişi gösterilmedi. Erişim talebi için yetkili biriminizle iletişime geçin."],
  }[state];
  return (
    <Alert
      action={state === "error" ? <Button color="inherit" onClick={onRefresh}>Yeniden dene</Button> : undefined}
      severity={state === "error" ? "error" : state === "unauthorized" ? "warning" : "info"}
    >
      <Typography sx={{ fontWeight: 700 }}>{content[0]}</Typography>
      <Typography variant="body2">{content[1]}</Typography>
    </Alert>
  );
}

export function ExecutionsPage({
  state = "normal",
  items = syntheticExecutions,
  correlationId,
  onRefresh,
}: ExecutionsPageProps) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [executionType, setExecutionType] = useState("ALL");
  const [period, setPeriod] = useState("ALL");
  const newestTime = Math.max(...items.map((item) => new Date(item.createdAt).getTime()));
  const visibleItems = useMemo(
    () => items.filter((item) => {
      const ageDays = (newestTime - new Date(item.createdAt).getTime()) / 86_400_000;
      return item.id.toLocaleLowerCase("tr-TR").includes(query.toLocaleLowerCase("tr-TR"))
        && (status === "ALL" || item.status === status)
        && (executionType === "ALL" || item.executionType === executionType)
        && (period === "ALL" || (period === "LATEST_DAY" ? ageDays < 1 : ageDays <= 7));
    }),
    [executionType, items, newestTime, period, query, status],
  );
  const effectiveItems = state === "long-content"
    ? Array.from({ length: 4 }, (_, group) => items.map((item) => ({
      ...item,
      id: `${item.id}-${group + 1}`,
    }))).flat()
    : visibleItems;

  return (
    <AppShell currentPage="Çalıştırmalar">
      <Box sx={(theme) => ({ display: "grid", gap: 5, margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 4, lg: 6 }, width: "100%" })}>
        <Box sx={{ alignItems: { md: "center" }, display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, justifyContent: "space-between" }}>
          <Box>
            <Typography component="h1" variant="h1">Çalıştırmalar</Typography>
            <Typography color="text.secondary">Yetkili kaynak kapsamınızdaki salt okunur çalışma geçmişi</Typography>
          </Box>
          {state !== "unauthorized" ? <Button onClick={onRefresh} startIcon={<RefreshCw aria-hidden="true" size={16} />} variant="contained">Yenile</Button> : null}
        </Box>

        {state !== "unauthorized" ? (
          <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
            <Box aria-label="Çalıştırma filtreleri" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(180px, 1fr))", lg: "minmax(240px, 1.4fr) repeat(4, minmax(145px, .7fr))" } }}>
              <TextField label="Çalıştırma ara" onChange={(event) => setQuery(event.target.value)} slotProps={{ input: { startAdornment: <Search aria-hidden="true" size={16} /> } }} value={query} />
              <FormControl><InputLabel id="execution-status-label">Durum</InputLabel><Select label="Durum" labelId="execution-status-label" onChange={(event) => setStatus(event.target.value)} value={status}><MenuItem value="ALL">Tüm durumlar</MenuItem>{Object.entries(statusLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <FormControl><InputLabel id="execution-type-label">Tür</InputLabel><Select label="Tür" labelId="execution-type-label" onChange={(event) => setExecutionType(event.target.value)} value={executionType}><MenuItem value="ALL">Tüm türler</MenuItem>{Object.entries(typeLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <FormControl><InputLabel id="execution-period-label">Tarih</InputLabel><Select label="Tarih" labelId="execution-period-label" onChange={(event) => setPeriod(event.target.value)} value={period}><MenuItem value="ALL">Tüm tarihler</MenuItem><MenuItem value="LATEST_DAY">Son kayıt günü</MenuItem><MenuItem value="LAST_7_DAYS">Son 7 gün</MenuItem></Select></FormControl>
              <FormControl><InputLabel id="execution-scope-label">Kapsam</InputLabel><Select disabled label="Kapsam" labelId="execution-scope-label" value="AUTHORIZED"><MenuItem value="AUTHORIZED">Yetkili kaynaklar</MenuItem></Select></FormControl>
            </Box>
          </Paper>
        ) : null}

        {state === "loading" ? <Box aria-busy="true" aria-label="Çalıştırmalar yükleniyor">{Array.from({ length: 6 }, (_, index) => <Skeleton height={84} key={index} />)}</Box> : null}
        {state === "empty" || state === "error" || state === "unauthorized" ? <StateMessage correlationId={correlationId} onRefresh={onRefresh} state={state} /> : null}
        {(state === "normal" || state === "long-content") && effectiveItems.length === 0 ? <StateMessage state="empty" /> : null}
        {(state === "normal" || state === "long-content") && effectiveItems.length > 0 ? (
          <Paper component="section" sx={{ borderRadius: 1.5, overflow: "hidden" }} variant="outlined">
            <Box sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
              <Typography component="h2" variant="h3">Çalıştırma Geçmişi</Typography>
              <Typography color="text.secondary" variant="body2">{effectiveItems.length} kayıt · en fazla 100</Typography>
            </Box>
            <Box
              aria-hidden="true"
              sx={{
                borderBottom: 1,
                borderColor: "divider",
                color: "text.secondary",
                display: { xs: "none", lg: "grid" },
                fontSize: "caption.fontSize",
                fontWeight: 700,
                gap: 3,
                gridTemplateColumns: "40px minmax(240px, 1.2fr) minmax(145px, .65fr) minmax(130px, .55fr) minmax(155px, .7fr) minmax(180px, .8fr)",
                px: 4,
                py: 2,
              }}
            >
              <Box />
              <Box>Çalıştırma</Box>
              <Box>Durum</Box>
              <Box>İş yükü</Box>
              <Box>Zaman</Box>
              <Box>Teknik sonuç</Box>
            </Box>
            <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>{effectiveItems.map((item) => <ExecutionRow item={item} key={item.id} />)}</Box>
          </Paper>
        ) : null}
      </Box>
    </AppShell>
  );
}
