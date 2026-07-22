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
  Braces,
  Clock3,
  KeyRound,
  ListChecks,
  RefreshCw,
  ScanText,
  Search,
  type LucideIcon,
} from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens } from "../theme/tokens";
import { syntheticRules, type RuleListItem, type RuleState } from "./model";

interface RulesPageProps {
  state?: RuleState;
  items?: RuleListItem[];
  correlationId?: string;
  onRefresh?: () => void;
}

const statusLabels: Record<string, string> = {
  DRAFT: "Taslak",
  ACTIVE: "Aktif",
  PASSIVE: "Pasif",
  REVIEW_REQUIRED: "İnceleme gerekli",
  ARCHIVED: "Arşivlendi",
};

const dimensionLabels: Record<string, string> = {
  COMPLETENESS: "Tamlık",
  ACCURACY: "Doğruluk",
  VALIDITY: "Geçerlilik",
  CONSISTENCY: "Tutarlılık",
  UNIQUENESS: "Tekillik",
  TIMELINESS: "Güncellik",
  INTEGRITY: "Bütünlük",
};

const criticalityLabels: Record<string, string> = {
  LOW: "Düşük",
  MEDIUM: "Orta",
  HIGH: "Yüksek",
  CRITICAL: "Kritik",
};

const ruleTypeLabels: Record<string, string> = {
  REQUIRED: "Zorunluluk",
  UNIQUE: "Tekillik",
  RANGE: "Aralık",
  REGEX: "Desen",
  FRESHNESS: "Güncellik",
  REFERENTIAL_INTEGRITY: "Referans bütünlüğü",
  CROSS_TABLE_CONSISTENCY: "Tablolar arası tutarlılık",
  CUSTOM_SQL: "Özel SQL",
};

function ruleIcon(ruleType: string): LucideIcon {
  if (ruleType === "FRESHNESS") return Clock3;
  if (ruleType === "REFERENTIAL_INTEGRITY") return KeyRound;
  if (ruleType === "REGEX") return ScanText;
  if (ruleType === "CUSTOM_SQL") return Braces;
  return ListChecks;
}

function statusTone(status: string): "success" | "warning" | "unknown" {
  if (status === "ACTIVE") return "success";
  if (status === "REVIEW_REQUIRED") return "warning";
  return "unknown";
}

function criticalityTone(
  criticality: string,
): "critical" | "warning" | "info" | "unknown" {
  if (criticality === "CRITICAL") return "critical";
  if (criticality === "HIGH") return "warning";
  if (criticality === "MEDIUM") return "info";
  return "unknown";
}

function RuleRow({ item }: { item: RuleListItem }) {
  const Icon = ruleIcon(item.ruleType);
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
          md: "40px minmax(260px, 1fr) minmax(145px, .65fr) minmax(110px, .5fr)",
          lg: "40px minmax(230px, 1.4fr) minmax(125px, .65fr) minmax(145px, .7fr) minmax(125px, .6fr) minmax(175px, .75fr)",
        },
        minHeight: 84,
        px: 4,
        py: 3,
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Box
        aria-hidden="true"
        data-testid="rule-icon-slot"
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
        <Typography color="text.secondary" noWrap variant="caption">
          {item.code} · {item.datasetId}
        </Typography>
      </Box>
      <Typography
        color="text.secondary"
        sx={{ display: { xs: "none", lg: "block" } }}
        variant="body2"
      >
        {dimensionLabels[item.dimension] ?? item.dimension}
      </Typography>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" } }}>
        <StatusBadge
          label={statusLabels[item.status] ?? item.status}
          tone={statusTone(item.status)}
        />
      </Box>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" } }}>
        <StatusBadge
          label={criticalityLabels[item.criticality] ?? item.criticality}
          tone={criticalityTone(item.criticality)}
        />
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" } }}>
        <Typography variant="body2">
          Sürüm {item.versionNo} · {ruleTypeLabels[item.ruleType] ?? item.ruleType}
        </Typography>
        <Typography color="text.secondary" variant="caption">
          {new Intl.DateTimeFormat("tr-TR", {
            dateStyle: "medium",
            timeStyle: "short",
          }).format(new Date(item.createdAt))}
        </Typography>
      </Box>
    </Box>
  );
}

function StateMessage({
  state,
  correlationId,
  onRefresh,
}: Pick<RulesPageProps, "correlationId" | "onRefresh"> & {
  state: "empty" | "error" | "unauthorized";
}) {
  const content = {
    empty: ["Kural bulunamadı", "Yetkili kapsam ve seçili filtrelerle eşleşen kural yok."],
    error: [
      "Kurallar yüklenemedi",
      `Teknik bir sorun oluştu. Yeniden deneyin. İzleme kodu: ${correlationId ?? "bulunamadı"}.`,
    ],
    unauthorized: [
      "Bu görünüm için yetkiniz yok",
      "Kural içeriği gösterilmedi. Erişim talebi için yetkili biriminizle iletişime geçin.",
    ],
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

export function RulesPage({
  state = "normal",
  items = syntheticRules,
  correlationId,
  onRefresh,
}: RulesPageProps) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [dimension, setDimension] = useState("ALL");
  const [criticality, setCriticality] = useState("ALL");
  const visibleItems = useMemo(
    () => items.filter((item) => {
      const searchable = `${item.name} ${item.code} ${item.datasetId} ${item.ruleType}`;
      return searchable.toLocaleLowerCase("tr-TR").includes(query.toLocaleLowerCase("tr-TR"))
        && (status === "ALL" || item.status === status)
        && (dimension === "ALL" || item.dimension === dimension)
        && (criticality === "ALL" || item.criticality === criticality);
    }),
    [criticality, dimension, items, query, status],
  );
  const effectiveItems = state === "long-content"
    ? Array.from({ length: 4 }, (_, group) => items.map((item) => ({
      ...item,
      id: `${item.id}-${group + 1}`,
      name: `${item.name} ${group + 1}`,
    }))).flat()
    : visibleItems;

  return (
    <AppShell currentPage="Kurallar">
      <Box sx={(theme) => ({ display: "grid", gap: 5, margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 4, lg: 6 }, width: "100%" })}>
        <Box sx={{ alignItems: { md: "center" }, display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, justifyContent: "space-between" }}>
          <Box>
            <Typography component="h1" variant="h1">Kurallar</Typography>
            <Typography color="text.secondary">Yetkili dataset kapsamınızdaki salt okunur kural envanteri</Typography>
          </Box>
          {state !== "unauthorized" ? <Button onClick={onRefresh} startIcon={<RefreshCw aria-hidden="true" size={16} />} variant="contained">Yenile</Button> : null}
        </Box>

        {state !== "unauthorized" ? (
          <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
            <Box aria-label="Kural filtreleri" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "minmax(240px, 1.4fr) repeat(3, minmax(150px, .7fr))" } }}>
              <TextField label="Kural ara" onChange={(event) => setQuery(event.target.value)} slotProps={{ input: { startAdornment: <Search aria-hidden="true" size={16} /> } }} value={query} />
              <FormControl><InputLabel id="rule-status-label">Durum</InputLabel><Select label="Durum" labelId="rule-status-label" onChange={(event) => setStatus(event.target.value)} value={status}><MenuItem value="ALL">Tüm durumlar</MenuItem>{Object.entries(statusLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <FormControl><InputLabel id="rule-dimension-label">Boyut</InputLabel><Select label="Boyut" labelId="rule-dimension-label" onChange={(event) => setDimension(event.target.value)} value={dimension}><MenuItem value="ALL">Tüm boyutlar</MenuItem>{Object.entries(dimensionLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <FormControl><InputLabel id="rule-criticality-label">Kritiklik</InputLabel><Select label="Kritiklik" labelId="rule-criticality-label" onChange={(event) => setCriticality(event.target.value)} value={criticality}><MenuItem value="ALL">Tüm seviyeler</MenuItem>{Object.entries(criticalityLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
            </Box>
          </Paper>
        ) : null}

        {state === "loading" ? <Box aria-busy="true" aria-label="Kurallar yükleniyor">{Array.from({ length: 5 }, (_, index) => <Skeleton height={84} key={index} />)}</Box> : null}
        {state === "empty" || state === "error" || state === "unauthorized" ? <StateMessage correlationId={correlationId} onRefresh={onRefresh} state={state} /> : null}
        {(state === "normal" || state === "long-content") && effectiveItems.length === 0 ? <StateMessage state="empty" /> : null}
        {(state === "normal" || state === "long-content") && effectiveItems.length > 0 ? (
          <Paper component="section" sx={{ borderRadius: 1.5, overflow: "hidden" }} variant="outlined">
            <Box sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
              <Typography component="h2" variant="h3">Kural Envanteri</Typography>
              <Typography color="text.secondary" variant="body2">{effectiveItems.length} kural</Typography>
            </Box>
            <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>{effectiveItems.map((item) => <RuleRow item={item} key={item.id} />)}</Box>
          </Paper>
        ) : null}
      </Box>
    </AppShell>
  );
}
