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
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { Braces, Database, FileSpreadsheet, RefreshCw, Search, type LucideIcon } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens } from "../theme/tokens";
import type { DataSourceListItem, DataSourceState } from "./model";
import { syntheticDataSources } from "./model";

interface DataSourcesPageProps {
  state?: DataSourceState;
  items?: DataSourceListItem[];
  correlationId?: string;
  onRefresh?: () => void;
}

const statusLabels: Record<string, string> = {
  ACTIVE: "Aktif",
  INACTIVE: "Pasif",
  TEST_PENDING: "Test Bekliyor",
  TEST_SUCCEEDED: "Test Başarılı",
  TEST_FAILED: "Test Başarısız",
  ARCHIVED: "Arşivlendi",
};

function sourceIcon(sourceType: string): LucideIcon {
  if (["CSV", "EXCEL"].includes(sourceType)) return FileSpreadsheet;
  if (sourceType === "REST") return Braces;
  return Database;
}

function sourceTone(status: string): "success" | "critical" | "warning" | "unknown" {
  if (["ACTIVE", "TEST_SUCCEEDED"].includes(status)) return "success";
  if (status === "TEST_FAILED") return "critical";
  if (status === "TEST_PENDING") return "warning";
  return "unknown";
}

function SourceRow({ item }: { item: DataSourceListItem }) {
  const Icon = sourceIcon(item.sourceType);
  return (
    <Box
      component="li"
      sx={{
        alignItems: "center",
        borderBottom: 1,
        borderColor: "divider",
        display: "grid",
        gap: 3,
        gridTemplateColumns: { xs: "40px minmax(0, 1fr)", md: "40px minmax(220px, 1.5fr) minmax(140px, .7fr) minmax(150px, .7fr) minmax(180px, .8fr)" },
        minHeight: 76,
        px: 4,
        py: 3,
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Box
        aria-hidden="true"
        data-testid="source-icon-slot"
        sx={(theme) => ({
          alignItems: "center",
          bgcolor: theme.status.infoSurface,
          borderRadius: 1,
          color: theme.status.info,
          display: "flex",
          height: 40,
          justifyContent: "center",
          width: 40,
        })}
      >
        <Icon size={designTokens.layout.navIconSize} strokeWidth={1.8} />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography noWrap sx={{ fontWeight: 700 }}>{item.name}</Typography>
        <Typography color="text.secondary" noWrap variant="caption">{item.id}</Typography>
      </Box>
      <Typography color="text.secondary" sx={{ gridColumn: { xs: "2", md: "auto" } }} variant="body2">{item.sourceType}</Typography>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" } }}>
        <StatusBadge label={statusLabels[item.status] ?? item.status} tone={sourceTone(item.status)} />
      </Box>
      <Typography color="text.secondary" sx={{ display: { xs: "none", md: "block" } }} variant="body2">
        {item.lastTestAt ? new Intl.DateTimeFormat("tr-TR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.lastTestAt)) : "Test edilmedi"}
      </Typography>
    </Box>
  );
}

function StateMessage({ state, correlationId, onRefresh }: Pick<DataSourcesPageProps, "correlationId" | "onRefresh"> & { state: "empty" | "error" | "unauthorized" }) {
  const content = {
    empty: ["Veri kaynağı bulunamadı", "Yetkili kapsam ve seçili filtrelerle eşleşen veri kaynağı yok."],
    error: ["Veri kaynakları yüklenemedi", `Teknik bir sorun oluştu. Yeniden deneyin. İzleme kodu: ${correlationId ?? "bulunamadı"}.`],
    unauthorized: ["Bu görünüm için yetkiniz yok", "Veri kaynağı içeriği gösterilmedi. Erişim talebi için yetkili biriminizle iletişime geçin."],
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

export function DataSourcesPage({ state = "normal", items = syntheticDataSources, correlationId, onRefresh }: DataSourcesPageProps) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [testPeriod, setTestPeriod] = useState("ALL");
  const visibleItems = useMemo(() => items.filter((item) => {
    const matchesQuery = `${item.name} ${item.id} ${item.sourceType}`.toLocaleLowerCase("tr-TR").includes(query.toLocaleLowerCase("tr-TR"));
    const matchesStatus = status === "ALL" || item.status === status;
    const matchesPeriod = testPeriod === "ALL" || (testPeriod === "UNTESTED" ? !item.lastTestAt : Boolean(item.lastTestAt && Date.now() - new Date(item.lastTestAt).getTime() <= 30 * 24 * 60 * 60 * 1000));
    return matchesQuery && matchesStatus && matchesPeriod;
  }), [items, query, status, testPeriod]);
  const effectiveItems = state === "long-content" ? Array.from({ length: 4 }, (_, group) => items.map((item) => ({ ...item, id: `${item.id}-${group + 1}`, name: `${item.name} ${group + 1}` }))).flat() : visibleItems;

  return (
    <AppShell currentPage="Veri Kaynakları">
      <Box sx={(theme) => ({ display: "grid", gap: 5, margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 4, lg: 6 }, width: "100%" })}>
        <Box sx={{ alignItems: { md: "center" }, display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, justifyContent: "space-between" }}>
          <Box>
            <Typography component="h1" variant="h1">Veri Kaynakları</Typography>
            <Typography color="text.secondary">Yetkili kapsamınızdaki salt okunur kaynak envanteri</Typography>
          </Box>
          {state !== "unauthorized" ? <Button onClick={onRefresh} startIcon={<RefreshCw aria-hidden="true" size={16} />} variant="contained">Yenile</Button> : null}
        </Box>

        {state !== "unauthorized" ? <Paper component="section" variant="outlined" sx={{ borderRadius: 1.5, p: 4 }}>
          <Box aria-label="Veri kaynağı filtreleri" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "minmax(240px, 1.4fr) repeat(3, minmax(160px, .7fr))" } }}>
            <TextField label="Kaynak ara" onChange={(event) => setQuery(event.target.value)} slotProps={{ input: { startAdornment: <Search aria-hidden="true" size={16} /> } }} value={query} />
            <FormControl><InputLabel id="source-status-label">Durum</InputLabel><Select label="Durum" labelId="source-status-label" onChange={(event) => setStatus(event.target.value)} value={status}><MenuItem value="ALL">Tüm durumlar</MenuItem>{Object.entries(statusLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
            <FormControl><InputLabel id="source-period-label">Son bağlantı testi</InputLabel><Select label="Son bağlantı testi" labelId="source-period-label" onChange={(event) => setTestPeriod(event.target.value)} value={testPeriod}><MenuItem value="ALL">Tüm tarihler</MenuItem><MenuItem value="LAST_30_DAYS">Son 30 gün</MenuItem><MenuItem value="UNTESTED">Test edilmemiş</MenuItem></Select></FormControl>
            <FormControl><InputLabel id="source-scope-label">Kapsam</InputLabel><Select disabled label="Kapsam" labelId="source-scope-label" value="AUTHORIZED"><MenuItem value="AUTHORIZED">Yetkili kaynaklar</MenuItem></Select></FormControl>
          </Box>
        </Paper> : null}

        {state === "loading" ? <Box aria-busy="true" aria-label="Veri kaynakları yükleniyor">{Array.from({ length: 4 }, (_, index) => <Skeleton height={76} key={index} />)}</Box> : null}
        {state === "empty" || state === "error" || state === "unauthorized" ? <StateMessage correlationId={correlationId} onRefresh={onRefresh} state={state} /> : null}
        {(state === "normal" || state === "long-content") && effectiveItems.length === 0 ? <StateMessage state="empty" /> : null}
        {(state === "normal" || state === "long-content") && effectiveItems.length > 0 ? (
          <Paper component="section" variant="outlined" sx={{ borderRadius: 1.5, overflow: "hidden" }}>
            <Box sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
              <Typography component="h2" variant="h3">Kaynak Envanteri</Typography>
              <Typography color="text.secondary" variant="body2">{effectiveItems.length} kaynak</Typography>
            </Box>
            <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>{effectiveItems.map((item) => <SourceRow item={item} key={item.id} />)}</Box>
          </Paper>
        ) : null}
      </Box>
    </AppShell>
  );
}
