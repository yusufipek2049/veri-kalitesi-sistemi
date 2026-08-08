import {
  Alert,
  Box,
  Button,
  Chip,
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
import { AlertFeed } from "../components/AlertFeed";
import { AppShell } from "../components/AppShell";
import { FieldScoreComparison } from "../components/FieldScoreComparison";
import { KpiCard } from "../components/KpiCard";
import { QualityDimensionMatrix } from "../components/QualityDimensionMatrix";
import { ScoreContributionPanel } from "../components/ScoreContributionPanel";
import { TrendPanel } from "../components/TrendPanel";
import {
  DASHBOARD_FILTER_LEVELS,
  DASHBOARD_FILTER_SCORE_STATUSES,
  DASHBOARD_FILTER_SCOPE_TYPES,
  longContentKpis,
  syntheticDashboardViewModel,
  type AppliedDashboardFilters,
  type DashboardFilterLevel,
  type DashboardFilterScoreStatus,
  type DashboardFilterScopeType,
  type DashboardFilters,
  type DashboardViewModel,
  type DashboardState,
} from "./model";

interface DashboardPageProps {
  state?: DashboardState;
  data?: DashboardViewModel;
  correlationId?: string;
  filters?: DashboardFilters;
  appliedFilters?: AppliedDashboardFilters | null;
  onRefresh?: () => void;
  onFiltersChange?: (filters: DashboardFilters) => void;
  onClearFilters?: () => void;
}

function LoadingDashboard({ data }: { data: DashboardViewModel }) {
  return (
    <Box aria-label="Dashboard yükleniyor" aria-busy="true">
      <Box sx={{ display: "grid", gap: 4, gridTemplateColumns: { md: "repeat(2, minmax(0, 1fr))", lg: "repeat(4, minmax(0, 1fr))" } }}>
        {data.kpis.map((item) => <Skeleton key={item.id} height={132} variant="rounded" />)}
      </Box>
      <Skeleton height={360} sx={{ mt: 5 }} variant="rounded" />
    </Box>
  );
}

function StateMessage({
  state,
  correlationId,
  onClearFilters,
}: {
  state: "empty" | "error" | "unauthorized" | "scope-forbidden" | "invalid-filter";
  correlationId?: string;
  onClearFilters?: () => void;
}) {
  const content = {
    empty: {
      severity: "info" as const,
      title: "Veri bulunamadı",
      body: "Seçili filtreler için hesaplanmış bir sonuç yok. Skor yerine sıfır gösterilmedi.",
      action: "Filtreleri temizle",
    },
    error: {
      severity: "error" as const,
      title: "Dashboard yüklenemedi",
      body: `Teknik bir sorun oluştu. Tarih aralığını daraltıp yeniden deneyin. İzleme kodu: ${correlationId ?? "bulunamadı"}.`,
      action: "Yeniden dene",
    },
    unauthorized: {
      severity: "warning" as const,
      title: "Bu görünüm için yetkiniz yok",
      body: "İstenen kapsamın içeriği gösterilmedi. Erişim talebi için yetkili biriminizle iletişime geçin.",
      action: "Genel bakışa dön",
    },
    "scope-forbidden": {
      severity: "warning" as const,
      title: "Seçili kapsama erişim yetkiniz yok",
      body: "İstenen kapsamın verisi sızdırılmadı. Yetkili biriminizden erişim talep edin.",
      action: "Filtreleri temizle",
    },
    "invalid-filter": {
      severity: "error" as const,
      title: "Geçersiz filtre parametresi",
      body: "URL'deki filtre değeri tanınmadı. Varsayılan görünüme dönüldü.",
      action: "Varsayılana dön",
    },
  }[state];

  const isTechnicalError = state === "error" || state === "invalid-filter";
  const showClearAction = state === "empty" || state === "scope-forbidden" || state === "invalid-filter";

  return (
    <Alert
      action={showClearAction ? <Button color="inherit" size="small" onClick={onClearFilters}>{content.action}</Button> : <Button color="inherit" size="small">{content.action}</Button>}
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

const scopeTypeLabels: Record<DashboardFilterScopeType, string> = {
  SOURCE: "Kaynak",
  ENTERPRISE: "Kurum",
};

const scoreStatusLabels: Record<DashboardFilterScoreStatus, string> = {
  CALCULATED: "Hesaplandı",
  NOT_CALCULATED: "Hesaplanmadı",
  NO_DATA: "Veri Yok",
  PARTIAL: "Kısmi",
  NOT_CALCULATED_TECHNICAL_ERROR: "Teknik Hata",
  CONFIG_ERROR: "Yapılandırma Hatası",
};

const levelLabels: Record<DashboardFilterLevel, string> = {
  GOOD: "İyi",
  ACCEPTABLE: "Kabul Edilebilir",
  RISKY: "Riskli",
  CRITICAL: "Kritik",
};

function DashboardFilterBar({
  filters,
  appliedFilters,
  onChange,
}: {
  filters: DashboardFilters;
  appliedFilters?: AppliedDashboardFilters | null;
  onChange: (filters: DashboardFilters) => void;
}) {
  return (
    <Paper aria-label="Dashboard filtreleri" component="section" sx={{ borderRadius: 1.5, p: 2 }} variant="outlined">
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(4, 1fr)" } }}>
        <FormControl size="small">
          <InputLabel id="filter-scope-type-label">Kapsam türü</InputLabel>
          <Select
            aria-label="Kapsam türü filtresi"
            label="Kapsam türü"
            labelId="filter-scope-type-label"
            onChange={(e) => onChange({ ...filters, scope_type: (e.target.value || undefined) as DashboardFilterScopeType | undefined })}
            value={filters.scope_type ?? ""}
          >
            <MenuItem value=""><em>Tümü</em></MenuItem>
            {DASHBOARD_FILTER_SCOPE_TYPES.map((type) => (
              <MenuItem key={type} value={type}>{scopeTypeLabels[type]}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField
          aria-label="Kaynak kimliği filtresi"
          label="Kaynak kimliği"
          onChange={(e) => onChange({ ...filters, scope_id: e.target.value || undefined })}
          placeholder="örn. source-a"
          size="small"
          value={filters.scope_id ?? ""}
        />
        <FormControl size="small">
          <InputLabel id="filter-score-status-label">Skor durumu</InputLabel>
          <Select
            aria-label="Skor durumu filtresi"
            label="Skor durumu"
            labelId="filter-score-status-label"
            onChange={(e) => onChange({ ...filters, score_status: (e.target.value || undefined) as DashboardFilterScoreStatus | undefined })}
            value={filters.score_status ?? ""}
          >
            <MenuItem value=""><em>Tümü</em></MenuItem>
            {DASHBOARD_FILTER_SCORE_STATUSES.map((status) => (
              <MenuItem key={status} value={status}>{scoreStatusLabels[status]}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small">
          <InputLabel id="filter-level-label">Kalite seviyesi</InputLabel>
          <Select
            aria-label="Kalite seviyesi filtresi"
            label="Kalite seviyesi"
            labelId="filter-level-label"
            onChange={(e) => onChange({ ...filters, level: (e.target.value || undefined) as DashboardFilterLevel | undefined })}
            value={filters.level ?? ""}
          >
            <MenuItem value=""><em>Tümü</em></MenuItem>
            {DASHBOARD_FILTER_LEVELS.map((lvl) => (
              <MenuItem key={lvl} value={lvl}>{levelLabels[lvl]}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>
      {appliedFilters && (
        <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1, mt: 2 }}>
          <Typography color="text.secondary" variant="caption">
            Pencere: {new Date(appliedFilters.window_start).toLocaleDateString("tr-TR")} – {new Date(appliedFilters.window_end).toLocaleDateString("tr-TR")}
          </Typography>
          {appliedFilters.scope_type && <Chip label={`Kapsam: ${appliedFilters.scope_type}${appliedFilters.scope_id ? ` (${appliedFilters.scope_id})` : ""}`} size="small" />}
          {appliedFilters.score_status && <Chip label={`Durum: ${scoreStatusLabels[appliedFilters.score_status as DashboardFilterScoreStatus] ?? appliedFilters.score_status}`} size="small" />}
          {appliedFilters.level && <Chip label={`Seviye: ${levelLabels[appliedFilters.level as DashboardFilterLevel] ?? appliedFilters.level}`} size="small" />}
        </Stack>
      )}
    </Paper>
  );
}

export function DashboardPage({
  state = "normal",
  data = syntheticDashboardViewModel,
  correlationId,
  filters,
  appliedFilters,
  onRefresh,
  onFiltersChange,
  onClearFilters,
}: DashboardPageProps) {
  const visibleKpis = state === "long-content" ? longContentKpis : data.kpis;
  const hasActiveFilters = filters && (filters.scope_type || filters.scope_id || filters.score_status || filters.level);

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
            <Typography color="text.secondary" variant="caption">
              {data.roleView === "ENGINEER" ? "Mühendis görünümü" : "Yönetici görünümü"}
            </Typography>
          </Box>
          <Stack direction="row" sx={{ flexWrap: "wrap", gap: 2 }}>
            {hasActiveFilters ? <Chip label="Filtreli" color="primary" onDelete={onClearFilters} variant="outlined" /> : null}
            <Button onClick={onRefresh} variant="contained">Yenile</Button>
          </Stack>
        </Box>

        <Alert severity="info" sx={{ py: 1 }}>
          {data.dataNotice}
        </Alert>

        {onFiltersChange ? (
          <DashboardFilterBar appliedFilters={appliedFilters} filters={filters ?? {}} onChange={onFiltersChange} />
        ) : null}

        {state === "loading" ? <LoadingDashboard data={data} /> : null}
        {state === "empty" || state === "error" || state === "unauthorized" || state === "scope-forbidden" || state === "invalid-filter" ? (
          <StateMessage correlationId={correlationId} onClearFilters={onClearFilters} state={state} />
        ) : null}

        {state === "normal" || state === "long-content" ? (
          <>
            <Box component="section" aria-label="Özet göstergeler" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))", lg: "repeat(4, minmax(0, 1fr))" } }}>
              {visibleKpis.map((item) => <KpiCard item={item} key={item.id} />)}
            </Box>
            <Box sx={{ display: "grid", gap: 4, gridTemplateColumns: { xs: "minmax(0, 1fr)", lg: "minmax(0, 2fr) minmax(320px, 1fr)" } }}>
              <TrendPanel description={data.trendDescription} observations={data.trendObservations} policyVersion={data.policyVersion} />
              <AlertFeed items={data.alerts} subtitle="Yetkili kapsam · veri-minimum görünüm" />
            </Box>
            <Box sx={{ display: "grid", gap: 4, gridTemplateColumns: { xs: "minmax(0, 1fr)", lg: "minmax(0, 1fr) minmax(0, 1.25fr)" } }}>
              <FieldScoreComparison items={data.fieldScores} />
              <QualityDimensionMatrix rows={data.qualityDimensionRows} />
            </Box>
            <Paper component="section" variant="outlined" sx={{ borderRadius: 1.5, p: 4 }}>
              <Typography component="h2" variant="h3">Ölçüm Notu</Typography>
              <Typography color="text.secondary" sx={{ mt: 2 }} variant="body2">
                {data.measurementNote}
              </Typography>
              <Typography color="text.secondary" sx={{ mt: 1 }} variant="body2">
                {data.comparisonNote}
              </Typography>
            </Paper>
            {data.roleView === "ENGINEER" ? (
              <ScoreContributionPanel
                components={data.contributionGraph?.components}
                profileVersion={data.contributionGraph?.versions?.profile_version}
                evidenceReferences={data.contributionGraph?.evidence_references}
                diagnosisStatus={data.contributionGraph?.diagnosis_status}
                diagnosisEvidenceRef={data.contributionGraph?.diagnosis_evidence_ref}
              />
            ) : (
              <Paper component="section" variant="outlined" sx={{ borderRadius: 1.5, p: 4 }}>
                <Typography component="h2" variant="h3">Yönetici Durum Özeti</Typography>
                <Box component="ul" sx={{ m: 0, mt: 2, pl: 3 }}>
                  <Typography component="li" variant="body2">
                    Kritik asset: {data.contributionGraph?.critical_asset_status ?? "UNKNOWN"}
                  </Typography>
                  <Typography component="li" variant="body2">
                    Bozulma: {data.contributionGraph?.deterioration_status ?? "UNKNOWN"}
                  </Typography>
                  <Typography component="li" variant="body2">
                    Risk: {data.contributionGraph?.risk_status ?? "UNKNOWN"}
                  </Typography>
                  <Typography component="li" variant="body2">
                    SLA: {data.contributionGraph?.sla_status ?? "UNKNOWN"}
                  </Typography>
                </Box>
                <Typography color="text.secondary" sx={{ mt: 2 }} variant="body2">
                  {data.governanceNote}
                </Typography>
              </Paper>
            )}
          </>
        ) : null}
      </Box>
    </AppShell>
  );
}
