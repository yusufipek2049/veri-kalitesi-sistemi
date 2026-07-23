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
  BadgeCheck,
  Ban,
  RefreshCw,
  ScrollText,
  ShieldCheck,
  ShieldX,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens, type StatusTone } from "../theme/tokens";
import {
  defaultAuditFilters,
  syntheticAuditPage,
  type AuditEventListItem,
  type AuditEventPage,
  type AuditQueryFilters,
  type AuditState,
} from "./model";

interface AuditPageProps {
  state?: AuditState;
  page?: AuditEventPage;
  correlationId?: string;
  onRefresh?: () => void;
  onQuery?: (filters: AuditQueryFilters) => void;
  onLoadMore?: () => void;
}

const resultLabels: Record<string, string> = {
  SUCCESS: "Başarılı",
  FAILURE: "Başarısız",
  DENIED: "Reddedildi",
};

const actionLabels: Record<string, string> = {
  LDAP_AUTHENTICATION: "Kimlik doğrulama",
  DATA_SOURCE_CONNECTION_TEST: "Bağlantı testi",
  RULE_ACTIVATION: "Kural aktivasyonu",
  SCORING_CONFIGURATION_ACTIVATION: "Skor politikası aktivasyonu",
  REPORT_PREVIEW_VIEWED: "Rapor önizleme",
  IDENTITY_SESSION: "Oturum olayı",
  AUDIT_RECORDS_VIEWED: "Denetim kaydı görüntüleme",
};

function resultPresentation(result: string): { icon: LucideIcon; tone: StatusTone } {
  if (result === "SUCCESS") return { icon: BadgeCheck, tone: "success" };
  if (result === "DENIED") return { icon: Ban, tone: "warning" };
  return { icon: Wrench, tone: "technical" };
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function EventRow({ item }: { item: AuditEventListItem }) {
  const presentation = resultPresentation(item.result);
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
          md: "40px minmax(220px, 1fr) minmax(135px, .55fr) minmax(150px, .62fr)",
          lg: "40px minmax(235px, 1fr) minmax(145px, .58fr) minmax(175px, .7fr) minmax(180px, .72fr) minmax(165px, .66fr)",
        },
        minHeight: 88,
        px: 4,
        py: 3,
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Box
        aria-hidden="true"
        data-testid="audit-icon-slot"
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
        <Typography noWrap sx={{ fontWeight: 700 }}>
          {actionLabels[item.action] ?? item.action}
        </Typography>
        <Typography color="text.secondary" noWrap variant="caption">
          {item.objectType}{item.objectId ? ` · ${item.objectId}` : ""}
        </Typography>
      </Box>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" } }}>
        <StatusBadge
          label={resultLabels[item.result] ?? item.result}
          tone={presentation.tone}
        />
      </Box>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" }, minWidth: 0 }}>
        <Typography noWrap variant="body2">{item.actorId}</Typography>
        <Typography color="text.secondary" variant="caption">
          {item.actorType ?? "Aktör türü yok"}
        </Typography>
        <Typography
          color="text.secondary"
          sx={{ display: { xs: "block", lg: "none" } }}
          variant="caption"
        >
          {" · "}{formatDate(item.occurredAt)}
        </Typography>
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" }, minWidth: 0 }}>
        <Typography noWrap variant="body2">{item.correlationId}</Typography>
        <Typography color="text.secondary" variant="caption">{item.reasonCode}</Typography>
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" } }}>
        <Typography variant="body2">{formatDate(item.occurredAt)}</Typography>
        <Typography color="text.secondary" variant="caption">Sıra #{item.sequenceNo}</Typography>
      </Box>
    </Box>
  );
}

function StateMessage({
  state,
  correlationId,
  onRefresh,
}: Pick<AuditPageProps, "correlationId" | "onRefresh"> & {
  state: "empty" | "error" | "unauthorized";
}) {
  const content = {
    empty: ["Denetim kaydı bulunamadı", "Seçili filtre ve çevrimiçi dönemle eşleşen kayıt yok."],
    error: ["Denetim kayıtları yüklenemedi", `Teknik bir sorun oluştu. Yeniden deneyin. İzleme kodu: ${correlationId ?? "bulunamadı"}.`],
    unauthorized: ["Bu görünüm için yetkiniz yok", "Denetim olayları ve bütünlük bilgisi gösterilmedi."],
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

export function AuditPage({
  state = "normal",
  page = syntheticAuditPage,
  correlationId,
  onRefresh,
  onQuery,
  onLoadMore,
}: AuditPageProps) {
  const [filters, setFilters] = useState<AuditQueryFilters>(defaultAuditFilters);
  const visibleItems = useMemo(
    () => page.items.filter((item) => (
      (!filters.actorId || item.actorId.toLocaleLowerCase("tr-TR").includes(filters.actorId.toLocaleLowerCase("tr-TR")))
      && (!filters.action || item.action.includes(filters.action.toLocaleUpperCase("tr-TR")))
      && (!filters.objectType || item.objectType.toLocaleLowerCase("tr-TR").includes(filters.objectType.toLocaleLowerCase("tr-TR")))
      && (filters.result === "ALL" || item.result === filters.result)
    )),
    [filters, page.items],
  );
  const effectiveItems = state === "long-content"
    ? Array.from({ length: 5 }, (_, group) => page.items.map((item) => ({
        ...item,
        eventId: `${item.eventId}-${group + 1}`,
        sequenceNo: item.sequenceNo + group * page.items.length,
      }))).flat()
    : visibleItems;
  const applyFilters = () => onQuery?.(filters);
  const resetFilters = () => {
    setFilters(defaultAuditFilters);
    onQuery?.(defaultAuditFilters);
  };

  return (
    <AppShell currentPage="Denetim">
      <Box sx={(theme) => ({ display: "grid", gap: 5, margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 4, lg: 6 }, width: "100%" })}>
        <Box sx={{ alignItems: { md: "center" }, display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, justifyContent: "space-between" }}>
          <Box>
            <Typography component="h1" variant="h1">Denetim</Typography>
            <Typography color="text.secondary">Yetkili çevrimiçi audit kayıtları ve zincir bütünlüğü</Typography>
          </Box>
          {state !== "unauthorized" ? <Button onClick={onRefresh} startIcon={<RefreshCw aria-hidden="true" size={16} />} variant="contained">Yenile</Button> : null}
        </Box>

        {state !== "unauthorized" ? (
          <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
            <Box aria-label="Denetim filtreleri" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(180px, 1fr))", lg: "repeat(5, minmax(155px, 1fr))" } }}>
              <TextField label="Aktör" onChange={(event) => setFilters((current) => ({ ...current, actorId: event.target.value }))} value={filters.actorId} />
              <TextField label="İşlem kodu" onChange={(event) => setFilters((current) => ({ ...current, action: event.target.value }))} value={filters.action} />
              <TextField label="Nesne türü" onChange={(event) => setFilters((current) => ({ ...current, objectType: event.target.value }))} value={filters.objectType} />
              <FormControl><InputLabel id="audit-result-label">Sonuç</InputLabel><Select label="Sonuç" labelId="audit-result-label" onChange={(event) => setFilters((current) => ({ ...current, result: event.target.value }))} value={filters.result}><MenuItem value="ALL">Tüm sonuçlar</MenuItem>{Object.entries(resultLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <FormControl><InputLabel id="audit-period-label">Dönem</InputLabel><Select label="Dönem" labelId="audit-period-label" onChange={(event) => setFilters((current) => ({ ...current, days: Number(event.target.value) }))} value={filters.days}><MenuItem value={1}>Son 24 saat</MenuItem><MenuItem value={7}>Son 7 gün</MenuItem><MenuItem value={30}>Son 30 gün</MenuItem></Select></FormControl>
            </Box>
            <Box sx={{ display: "flex", gap: 2, justifyContent: "flex-end", mt: 3 }}>
              <Button onClick={resetFilters} size="small">Filtreleri temizle</Button>
              <Button onClick={applyFilters} size="small" variant="contained">Uygula</Button>
            </Box>
          </Paper>
        ) : null}

        {state === "loading" ? <Box aria-busy="true" aria-label="Denetim kayıtları yükleniyor">{Array.from({ length: 6 }, (_, index) => <Skeleton height={88} key={index} />)}</Box> : null}
        {state === "empty" || state === "error" || state === "unauthorized" ? <StateMessage correlationId={correlationId} onRefresh={onRefresh} state={state} /> : null}

        {(state === "normal" || state === "long-content") ? (
          <>
            <Box aria-label="Denetim özeti" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" } }}>
              <Paper
                component="section"
                sx={(theme) => ({
                  bgcolor: theme.status[page.integrityValid ? "successSurface" : "criticalSurface"],
                  borderColor: theme.status[page.integrityValid ? "success" : "critical"],
                  borderRadius: 1.5,
                  color: theme.status[page.integrityValid ? "success" : "critical"],
                  minHeight: 116,
                  p: 4,
                  "& .MuiTypography-root": { color: "inherit" },
                })}
                variant="outlined"
              >
                {page.integrityValid ? <ShieldCheck aria-hidden="true" size={20} /> : <ShieldX aria-hidden="true" size={20} />}
                <Typography sx={{ mt: 2 }} variant="h3">{page.integrityValid ? "Bütünlük doğrulandı" : "Bütünlük sorunu"}</Typography>
                <Typography variant="caption">{page.integrityCheckedCount} kayıt kontrol edildi</Typography>
              </Paper>
              <Paper component="section" sx={{ borderRadius: 1.5, minHeight: 116, p: 4 }} variant="outlined">
                <ScrollText aria-hidden="true" size={20} />
                <Typography sx={{ mt: 2 }} variant="h2">{effectiveItems.length}</Typography>
                <Typography color="text.secondary" variant="caption">Görüntülenen olay · sayfa sınırı {page.pageSize}</Typography>
              </Paper>
              <Paper component="section" sx={{ borderRadius: 1.5, minHeight: 116, p: 4 }} variant="outlined">
                <Typography color="text.secondary" variant="body2">Çevrimiçi dönem</Typography>
                <Typography sx={{ mt: 2 }} variant="h3">{filters.days} gün</Typography>
                <Typography color="text.secondary" variant="caption">Snapshot #{page.throughSequenceNo} · {page.policyVersion}</Typography>
              </Paper>
            </Box>

            {!page.integrityValid ? <Alert severity="error"><Typography sx={{ fontWeight: 700 }}>Audit zinciri bütünlük kontrolünden geçmedi</Typography><Typography variant="body2">Kayıtlar değiştirilmedi. Güvenlik incelemesi gereklidir.</Typography></Alert> : null}

            {effectiveItems.length === 0 ? <StateMessage state="empty" /> : (
              <Paper component="section" sx={{ borderRadius: 1.5, overflow: "hidden" }} variant="outlined">
                <Box sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
                  <Box>
                    <Typography component="h2" variant="h3">Audit Olayları</Typography>
                    <Typography color="text.secondary" variant="caption">{formatDate(page.periodStart)} – {formatDate(page.periodEnd)}</Typography>
                  </Box>
                  <Typography color="text.secondary" variant="body2">{effectiveItems.length} kayıt</Typography>
                </Box>
                <Box aria-hidden="true" sx={{ borderBottom: 1, borderColor: "divider", color: "text.secondary", display: { xs: "none", lg: "grid" }, fontSize: "caption.fontSize", fontWeight: 700, gap: 3, gridTemplateColumns: "40px minmax(235px, 1fr) minmax(145px, .58fr) minmax(175px, .7fr) minmax(180px, .72fr) minmax(165px, .66fr)", px: 4, py: 2 }}>
                  <Box /><Box>İşlem ve nesne</Box><Box>Sonuç</Box><Box>Aktör</Box><Box>İlişki ve gerekçe</Box><Box>Zaman</Box>
                </Box>
                <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>{effectiveItems.map((item) => <EventRow item={item} key={item.eventId} />)}</Box>
                {page.nextAfterSequenceNo !== null ? <Box sx={{ borderTop: 1, borderColor: "divider", display: "flex", justifyContent: "center", p: 3 }}><Button onClick={onLoadMore}>Daha fazla göster</Button></Box> : null}
              </Paper>
            )}
          </>
        ) : null}
      </Box>
    </AppShell>
  );
}
