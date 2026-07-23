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
  AlertTriangle,
  BadgeCheck,
  Ban,
  CircleDot,
  CircleEllipsis,
  RefreshCw,
  Search,
  ShieldAlert,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens, type StatusTone } from "../theme/tokens";
import { syntheticIssues, type IssueListItem, type IssueState } from "./model";

interface IssuesPageProps {
  state?: IssueState;
  items?: IssueListItem[];
  correlationId?: string;
  onRefresh?: () => void;
}

const statusLabels: Record<string, string> = {
  NEW: "Yeni",
  ASSIGNED: "Atandı",
  INVESTIGATING: "İnceleniyor",
  WAITING_FOR_RESOLUTION: "Çözüm bekliyor",
  RESOLVED: "Çözüldü",
  VERIFIED: "Doğrulandı",
  CLOSED: "Kapatıldı",
  CANCELLED: "İptal edildi",
};

const priorityLabels: Record<string, string> = {
  LOW: "Düşük",
  MEDIUM: "Orta",
  HIGH: "Yüksek",
  CRITICAL: "Kritik",
};

const triggerLabels: Record<string, string> = {
  QUALITY_THRESHOLD: "Kalite eşiği",
  CRITICAL_RULE_FAILURE: "Kritik kontrol",
  TECHNICAL_ERROR: "Teknik olay",
};

function statusTone(status: string): StatusTone {
  if (status === "RESOLVED" || status === "VERIFIED") return "success";
  if (status === "INVESTIGATING" || status === "ASSIGNED") return "info";
  if (status === "WAITING_FOR_RESOLUTION") return "warning";
  return "unknown";
}

function priorityTone(priority: string): StatusTone {
  if (priority === "CRITICAL") return "critical";
  if (priority === "HIGH") return "warning";
  if (priority === "MEDIUM") return "info";
  return "unknown";
}

function issuePresentation(item: IssueListItem): { icon: LucideIcon; tone: StatusTone } {
  if (item.sourceEventType === "TECHNICAL") return { icon: Wrench, tone: "technical" };
  if (item.priority === "CRITICAL") return { icon: ShieldAlert, tone: "critical" };
  if (item.status === "VERIFIED" || item.status === "RESOLVED") {
    return { icon: BadgeCheck, tone: "success" };
  }
  if (item.status === "CANCELLED") return { icon: Ban, tone: "unknown" };
  if (item.status === "INVESTIGATING") return { icon: CircleEllipsis, tone: "info" };
  if (item.priority === "HIGH") return { icon: AlertTriangle, tone: "warning" };
  return { icon: CircleDot, tone: "info" };
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function IssueRow({ item }: { item: IssueListItem }) {
  const presentation = issuePresentation(item);
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
          md: "40px minmax(210px, 1fr) minmax(140px, .6fr) minmax(120px, .5fr)",
          lg: "40px minmax(220px, 1fr) minmax(140px, .62fr) minmax(120px, .5fr) minmax(185px, .8fr) minmax(165px, .7fr)",
        },
        minHeight: 88,
        px: 4,
        py: 3,
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Box
        aria-hidden="true"
        data-testid="issue-icon-slot"
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
        <Typography noWrap sx={{ fontWeight: 700 }}>{item.issueNo}</Typography>
        <Typography color="text.secondary" noWrap variant="caption">
          {triggerLabels[item.triggerType] ?? item.triggerType} · {item.occurrenceCount} görülme
        </Typography>
      </Box>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" } }}>
        <Typography color="text.secondary" sx={{ display: { xs: "block", lg: "none" } }} variant="caption">
          Durum
        </Typography>
        <StatusBadge
          label={statusLabels[item.status] ?? item.status}
          tone={statusTone(item.status)}
        />
      </Box>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" } }}>
        <Typography color="text.secondary" sx={{ display: { xs: "block", lg: "none" } }} variant="caption">
          Öncelik
        </Typography>
        <StatusBadge
          label={priorityLabels[item.priority] ?? item.priority}
          tone={priorityTone(item.priority)}
        />
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" }, minWidth: 0 }}>
        <Typography noWrap variant="body2">{item.scopeId}</Typography>
        <Typography color="text.secondary" variant="caption">
          {item.scopeType === "SOURCE" ? "Veri kaynağı" : "Dataset"} · {item.sourceEventType === "TECHNICAL" ? "Teknik" : "Kalite"}
        </Typography>
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" } }}>
        <Typography variant="body2">{formatDate(item.updatedAt)}</Typography>
        <Typography color="text.secondary" variant="caption">
          Son görülme: {formatDate(item.lastSeenAt)}
        </Typography>
      </Box>
    </Box>
  );
}

function StateMessage({
  state,
  correlationId,
  onRefresh,
}: Pick<IssuesPageProps, "correlationId" | "onRefresh"> & {
  state: "empty" | "error" | "unauthorized";
}) {
  const content = {
    empty: ["Sorun bulunamadı", "Yetkili kapsam ve seçili filtrelerle eşleşen sorun yok."],
    error: ["Sorunlar yüklenemedi", `Teknik bir sorun oluştu. Yeniden deneyin. İzleme kodu: ${correlationId ?? "bulunamadı"}.`],
    unauthorized: ["Bu görünüm için yetkiniz yok", "Sorun envanteri gösterilmedi. Erişim talebi için yetkili biriminizle iletişime geçin."],
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

export function IssuesPage({
  state = "normal",
  items = syntheticIssues,
  correlationId,
  onRefresh,
}: IssuesPageProps) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [priority, setPriority] = useState("ALL");
  const [period, setPeriod] = useState("ALL");
  const newestTime = items.length
    ? Math.max(...items.map((item) => new Date(item.updatedAt).getTime()))
    : 0;
  const visibleItems = useMemo(
    () => items.filter((item) => {
      const searchable = `${item.issueNo} ${item.scopeId}`.toLocaleLowerCase("tr-TR");
      const ageDays = (newestTime - new Date(item.updatedAt).getTime()) / 86_400_000;
      return searchable.includes(query.toLocaleLowerCase("tr-TR"))
        && (status === "ALL" || item.status === status)
        && (priority === "ALL" || item.priority === priority)
        && (period === "ALL" || (period === "LATEST_DAY" ? ageDays < 1 : ageDays <= 7));
    }),
    [items, newestTime, period, priority, query, status],
  );
  const effectiveItems = state === "long-content"
    ? Array.from({ length: 4 }, (_, group) => items.map((item) => ({
      ...item,
      id: `${item.id}-${group + 1}`,
      issueNo: `${item.issueNo}-${group + 1}`,
    }))).flat()
    : visibleItems;
  const resetFilters = () => {
    setQuery("");
    setStatus("ALL");
    setPriority("ALL");
    setPeriod("ALL");
  };

  return (
    <AppShell currentPage="Sorunlar">
      <Box sx={(theme) => ({ display: "grid", gap: 5, margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 4, lg: 6 }, width: "100%" })}>
        <Box sx={{ alignItems: { md: "center" }, display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, justifyContent: "space-between" }}>
          <Box>
            <Typography component="h1" variant="h1">Sorunlar</Typography>
            <Typography color="text.secondary">Yetkili kapsamınızdaki kalite ve teknik sorunların salt okunur envanteri</Typography>
          </Box>
          {state !== "unauthorized" ? <Button onClick={onRefresh} startIcon={<RefreshCw aria-hidden="true" size={16} />} variant="contained">Yenile</Button> : null}
        </Box>

        {state !== "unauthorized" ? (
          <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
            <Box aria-label="Sorun filtreleri" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(180px, 1fr))", lg: "minmax(230px, 1.35fr) repeat(4, minmax(145px, .7fr))" } }}>
              <TextField label="Sorun ara" onChange={(event) => setQuery(event.target.value)} slotProps={{ input: { startAdornment: <Search aria-hidden="true" size={16} /> } }} value={query} />
              <FormControl><InputLabel id="issue-status-label">Durum</InputLabel><Select label="Durum" labelId="issue-status-label" onChange={(event) => setStatus(event.target.value)} value={status}><MenuItem value="ALL">Tüm durumlar</MenuItem>{Object.entries(statusLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <FormControl><InputLabel id="issue-priority-label">Öncelik</InputLabel><Select label="Öncelik" labelId="issue-priority-label" onChange={(event) => setPriority(event.target.value)} value={priority}><MenuItem value="ALL">Tüm öncelikler</MenuItem>{Object.entries(priorityLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <FormControl><InputLabel id="issue-period-label">Tarih</InputLabel><Select label="Tarih" labelId="issue-period-label" onChange={(event) => setPeriod(event.target.value)} value={period}><MenuItem value="ALL">Tüm tarihler</MenuItem><MenuItem value="LATEST_DAY">Son güncellenen gün</MenuItem><MenuItem value="LAST_7_DAYS">Son 7 gün</MenuItem></Select></FormControl>
              <FormControl><InputLabel id="issue-scope-label">Kapsam</InputLabel><Select disabled label="Kapsam" labelId="issue-scope-label" value="AUTHORIZED"><MenuItem value="AUTHORIZED">Yetkili kapsam</MenuItem></Select></FormControl>
            </Box>
            <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 3 }}>
              <Button onClick={resetFilters} size="small">Filtreleri temizle</Button>
            </Box>
          </Paper>
        ) : null}

        {state === "loading" ? <Box aria-busy="true" aria-label="Sorunlar yükleniyor">{Array.from({ length: 6 }, (_, index) => <Skeleton height={88} key={index} />)}</Box> : null}
        {state === "empty" || state === "error" || state === "unauthorized" ? <StateMessage correlationId={correlationId} onRefresh={onRefresh} state={state} /> : null}
        {(state === "normal" || state === "long-content") && effectiveItems.length === 0 ? <StateMessage state="empty" /> : null}
        {(state === "normal" || state === "long-content") && effectiveItems.length > 0 ? (
          <Paper component="section" sx={{ borderRadius: 1.5, overflow: "hidden" }} variant="outlined">
            <Box sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
              <Typography component="h2" variant="h3">Sorun Envanteri</Typography>
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
                gridTemplateColumns: "40px minmax(220px, 1fr) minmax(140px, .62fr) minmax(120px, .5fr) minmax(185px, .8fr) minmax(165px, .7fr)",
                px: 4,
                py: 2,
              }}
            >
              <Box />
              <Box>Sorun</Box>
              <Box>Durum</Box>
              <Box>Öncelik</Box>
              <Box>Kapsam ve tür</Box>
              <Box>Son hareket</Box>
            </Box>
            <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>{effectiveItems.map((item) => <IssueRow item={item} key={item.id} />)}</Box>
          </Paper>
        ) : null}
      </Box>
    </AppShell>
  );
}
