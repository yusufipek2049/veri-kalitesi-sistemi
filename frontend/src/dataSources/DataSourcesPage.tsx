import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
  Check,
  Database,
  FileSpreadsheet,
  Play,
  Plus,
  Power,
  PowerOff,
  RefreshCw,
  Search,
  X,
  Braces,
  ScanSearch,
  type LucideIcon,
} from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens } from "../theme/tokens";
import { dataSourceErrorMessage } from "./api";
import {
  syntheticDataSources,
  type DataSourceAction,
  type DataSourceCreateRequest,
  type DataSourceListItem,
  type DataSourceState,
} from "./model";

interface DataSourcesPageProps {
  state?: DataSourceState;
  items?: DataSourceListItem[];
  correlationId?: string;
  onRefresh?: () => void;
  onCreate?: (payload: DataSourceCreateRequest) => Promise<void>;
  onTest?: (dataSourceId: string) => Promise<void>;
  onRequestActivation?: (dataSourceId: string) => Promise<void>;
  onDecideActivation?: (
    activationRequestId: string,
    decision: "APPROVE" | "REJECT",
    reasonCode: string,
  ) => Promise<void>;
  onPassivate?: (dataSourceId: string, reasonCode: string) => Promise<void>;
  onDiscoverMetadata?: (dataSourceId: string) => Promise<void>;
}

const statusLabels: Record<string, string> = {
  ACTIVE: "Aktif",
  INACTIVE: "Pasif",
  TEST_PENDING: "Test Bekliyor",
  TEST_SUCCEEDED: "Test Başarılı",
  TEST_FAILED: "Test Başarısız",
  ARCHIVED: "Arşivlendi",
};

const actionLabels: Record<DataSourceAction, string> = {
  TEST_CONNECTION: "Bağlantıyı test et",
  REQUEST_ACTIVATION: "Aktivasyon talep et",
  APPROVE_ACTIVATION: "Onayla",
  REJECT_ACTIVATION: "Reddet",
  PASSIVATE: "Pasifleştir",
  DISCOVER_METADATA: "Metadata keşfet",
};

const actionIcons: Record<DataSourceAction, LucideIcon> = {
  TEST_CONNECTION: Play,
  REQUEST_ACTIVATION: Power,
  APPROVE_ACTIVATION: Check,
  REJECT_ACTIVATION: X,
  PASSIVATE: PowerOff,
  DISCOVER_METADATA: ScanSearch,
};

const emptyCreateForm: DataSourceCreateRequest = {
  name: "",
  source_type: "POSTGRESQL",
  host: "",
  port: 5432,
  database: "",
  schema: "public",
  secret_reference: "",
  ssl_mode: "verify-full",
  connect_timeout_seconds: 5,
  statement_timeout_ms: 5000,
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

function SourceRow({
  item,
  actionLoading,
  onAction,
}: {
  item: DataSourceListItem;
  actionLoading: string | null;
  onAction: (item: DataSourceListItem, action: DataSourceAction) => void;
}) {
  const Icon = sourceIcon(item.sourceType);
  return (
    <Box component="li" sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "grid", gap: 3, gridTemplateColumns: { xs: "40px minmax(0, 1fr)", md: "40px minmax(180px, 1fr) 120px 130px minmax(170px, auto)" }, minHeight: 76, px: 4, py: 3, "&:last-child": { borderBottom: 0 } }}>
      <Box aria-hidden="true" data-testid="source-icon-slot" sx={(theme) => ({ alignItems: "center", bgcolor: theme.status.infoSurface, borderRadius: 1, color: theme.status.info, display: "flex", height: 40, justifyContent: "center", width: 40 })}>
        <Icon size={designTokens.layout.navIconSize} strokeWidth={1.8} />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography noWrap sx={{ fontWeight: 700 }}>{item.name}</Typography>
        <Typography color="text.secondary" noWrap variant="caption">{item.id}</Typography>
      </Box>
      <Typography color="text.secondary" variant="body2">{item.sourceType}</Typography>
      <StatusBadge label={statusLabels[item.status] ?? item.status} tone={sourceTone(item.status)} />
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, justifyContent: "flex-end" }}>
        {item.availableActions.map((action) => {
          const ActionIcon = actionIcons[action];
          const loading = actionLoading === `${item.id}:${action}`;
          return (
            <Button
              aria-label={actionLabels[action]}
              disabled={loading}
              key={action}
              onClick={() => onAction(item, action)}
              size="small"
              startIcon={<ActionIcon aria-hidden="true" size={16} />}
              variant="outlined"
            >
              {actionLabels[action]}
            </Button>
          );
        })}
      </Box>
    </Box>
  );
}

function StateMessage({ state, correlationId, onRefresh }: Pick<DataSourcesPageProps, "correlationId" | "onRefresh"> & { state: "empty" | "error" | "unauthorized" }) {
  const content = {
    empty: ["Veri kaynağı bulunamadı", "Yetkili kapsamınızda veri kaynağı yok."],
    error: ["Veri kaynakları yüklenemedi", `Teknik bir sorun oluştu. İzleme kodu: ${correlationId ?? "bulunamadı"}.`],
    unauthorized: ["Bu görünüm için yetkiniz yok", "Veri kaynağı içeriği gösterilmedi."],
  }[state];
  return (
    <Alert action={state === "error" ? <Button color="inherit" onClick={onRefresh}>Yeniden dene</Button> : undefined} severity={state === "error" ? "error" : state === "unauthorized" ? "warning" : "info"}>
      <Typography sx={{ fontWeight: 700 }}>{content[0]}</Typography>
      <Typography variant="body2">{content[1]}</Typography>
    </Alert>
  );
}

export function DataSourcesPage({
  state = "normal",
  items = syntheticDataSources,
  correlationId,
  onRefresh,
  onCreate,
  onTest,
  onRequestActivation,
  onDecideActivation,
  onPassivate,
  onDiscoverMetadata,
}: DataSourcesPageProps) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [form, setForm] = useState<DataSourceCreateRequest>({ ...emptyCreateForm });
  const [connectionParameters, setConnectionParameters] = useState("");
  const [passivationSource, setPassivationSource] = useState<DataSourceListItem | null>(null);
  const [passivationReason, setPassivationReason] = useState("");
  const [decision, setDecision] = useState<{ item: DataSourceListItem; value: "APPROVE" | "REJECT" } | null>(null);
  const [decisionReason, setDecisionReason] = useState("");

  const visibleItems = useMemo(() => items.filter((item) => {
    const matchesQuery = `${item.name} ${item.id} ${item.sourceType}`.toLocaleLowerCase("tr-TR").includes(query.toLocaleLowerCase("tr-TR"));
    return matchesQuery && (status === "ALL" || item.status === status);
  }), [items, query, status]);
  const effectiveItems = state === "long-content"
    ? Array.from({ length: 4 }, (_, group) => items.map((item) => ({ ...item, id: `${item.id}-${group + 1}`, name: `${item.name} ${group + 1}` }))).flat()
    : visibleItems;

  const run = async (key: string, operation: () => Promise<void>) => {
    setActionLoading(key);
    setActionError(null);
    try {
      await operation();
    } catch (error) {
      setActionError(dataSourceErrorMessage(error));
      throw error;
    } finally {
      setActionLoading(null);
    }
  };

  const handleAction = (item: DataSourceListItem, action: DataSourceAction) => {
    if (action === "TEST_CONNECTION" && onTest) void run(`${item.id}:${action}`, () => onTest(item.id)).catch(() => undefined);
    if (action === "REQUEST_ACTIVATION" && onRequestActivation) void run(`${item.id}:${action}`, () => onRequestActivation(item.id)).catch(() => undefined);
    if (action === "PASSIVATE") {
      setPassivationReason("");
      setPassivationSource(item);
    }
    if (action === "DISCOVER_METADATA" && onDiscoverMetadata) {
      void run(`${item.id}:${action}`, () => onDiscoverMetadata(item.id)).catch(() => undefined);
    }
    if (action === "APPROVE_ACTIVATION" || action === "REJECT_ACTIVATION") {
      setDecisionReason("");
      setDecision({ item, value: action === "APPROVE_ACTIVATION" ? "APPROVE" : "REJECT" });
    }
  };

  const submitCreate = async () => {
    if (!onCreate) return;
    let parsed: Record<string, unknown> | undefined;
    try {
      parsed = connectionParameters.trim() ? JSON.parse(connectionParameters) as Record<string, unknown> : undefined;
    } catch {
      setCreateError("Bağlantı parametreleri geçerli JSON olmalıdır.");
      return;
    }
    setCreateLoading(true);
    setCreateError(null);
    try {
      await onCreate({ ...form, connection_parameters: parsed });
      setCreateOpen(false);
      setForm({ ...emptyCreateForm });
      setConnectionParameters("");
    } catch (error) {
      setCreateError(dataSourceErrorMessage(error));
    } finally {
      setCreateLoading(false);
    }
  };

  const submitPassivation = async () => {
    if (!passivationSource || !onPassivate) return;
    const source = passivationSource;
    try {
      await run(`${source.id}:PASSIVATE`, () => onPassivate(source.id, passivationReason.trim()));
      setPassivationSource(null);
    } catch {
      // Error is rendered by the shared action alert.
    }
  };

  const submitDecision = async () => {
    if (!decision || !onDecideActivation || !decision.item.pendingActivationRequestId) return;
    try {
      await run(`${decision.item.id}:${decision.value}`, () => onDecideActivation(decision.item.pendingActivationRequestId!, decision.value, decisionReason.trim()));
      setDecision(null);
    } catch {
      // Error is rendered by the shared action alert.
    }
  };

  return (
    <AppShell currentPage="Veri Kaynakları">
      <Box sx={(theme) => ({ display: "grid", gap: 5, margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 4, lg: 6 }, width: "100%" })}>
        <Box sx={{ alignItems: { md: "center" }, display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, justifyContent: "space-between" }}>
          <Box><Typography component="h1" variant="h1">Veri Kaynakları</Typography><Typography color="text.secondary">Yetkili kapsamınızdaki kaynak envanteri</Typography></Box>
          <Box sx={{ display: "flex", gap: 2 }}>
            {onCreate ? <Button onClick={() => { setCreateError(null); setCreateOpen(true); }} startIcon={<Plus aria-hidden="true" size={16} />} variant="contained">Yeni veri kaynağı</Button> : null}
            {state !== "unauthorized" ? <Button onClick={onRefresh} startIcon={<RefreshCw aria-hidden="true" size={16} />} variant="outlined">Yenile</Button> : null}
          </Box>
        </Box>
        {actionError ? <Alert onClose={() => setActionError(null)} severity="error">{actionError}</Alert> : null}
        {state !== "unauthorized" ? <Paper component="section" variant="outlined" sx={{ borderRadius: 1.5, p: 4 }}><Box aria-label="Veri kaynağı filtreleri" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "2fr 1fr" } }}><TextField label="Kaynak ara" onChange={(event) => setQuery(event.target.value)} slotProps={{ input: { startAdornment: <Search aria-hidden="true" size={16} /> } }} value={query} /><FormControl><InputLabel id="source-status-label">Durum</InputLabel><Select label="Durum" labelId="source-status-label" onChange={(event) => setStatus(event.target.value)} value={status}><MenuItem value="ALL">Tüm durumlar</MenuItem>{Object.entries(statusLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl></Box></Paper> : null}
        {state === "loading" ? <Box aria-busy="true" aria-label="Veri kaynakları yükleniyor">{Array.from({ length: 4 }, (_, index) => <Skeleton height={76} key={index} />)}</Box> : null}
        {state === "empty" || state === "error" || state === "unauthorized" ? <StateMessage correlationId={correlationId} onRefresh={onRefresh} state={state} /> : null}
        {(state === "normal" || state === "long-content") && effectiveItems.length === 0 ? <StateMessage state="empty" /> : null}
        {(state === "normal" || state === "long-content") && effectiveItems.length > 0 ? <Paper component="section" variant="outlined" sx={{ borderRadius: 1.5, overflow: "hidden" }}><Box sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}><Typography component="h2" variant="h3">Kaynak Envanteri</Typography><Typography color="text.secondary" variant="body2">{effectiveItems.length} kaynak</Typography></Box><Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>{effectiveItems.map((item) => <SourceRow actionLoading={actionLoading} item={item} key={item.id} onAction={handleAction} />)}</Box></Paper> : null}

        <Dialog fullWidth maxWidth="sm" onClose={() => !createLoading && setCreateOpen(false)} open={createOpen}>
          <DialogTitle>Yeni PostgreSQL veri kaynağı</DialogTitle>
          <DialogContent><Box sx={{ display: "grid", gap: 2, mt: 1 }}>
            <TextField label="Kaynak adı" onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required value={form.name} />
            <TextField label="Sunucu" onChange={(e) => setForm((f) => ({ ...f, host: e.target.value }))} required value={form.host} />
            <TextField label="Port" onChange={(e) => setForm((f) => ({ ...f, port: Number(e.target.value) }))} required type="number" value={form.port} />
            <TextField label="Veritabanı" onChange={(e) => setForm((f) => ({ ...f, database: e.target.value }))} required value={form.database} />
            <TextField label="Şema" onChange={(e) => setForm((f) => ({ ...f, schema: e.target.value }))} required value={form.schema} />
            <TextField helperText="Örnek: secret://local/source-a" label="Secret referansı" onChange={(e) => setForm((f) => ({ ...f, secret_reference: e.target.value }))} required value={form.secret_reference} />
            <FormControl><InputLabel id="ssl-mode-label">TLS doğrulama modu</InputLabel><Select label="TLS doğrulama modu" labelId="ssl-mode-label" onChange={(e) => setForm((f) => ({ ...f, ssl_mode: e.target.value as DataSourceCreateRequest["ssl_mode"] }))} value={form.ssl_mode}><MenuItem value="verify-full">verify-full</MenuItem><MenuItem value="verify-ca">verify-ca</MenuItem><MenuItem value="require">require</MenuItem></Select></FormControl>
            <TextField label="Bağlantı zaman aşımı (sn)" onChange={(e) => setForm((f) => ({ ...f, connect_timeout_seconds: Number(e.target.value) }))} type="number" value={form.connect_timeout_seconds} />
            <TextField label="Sorgu zaman aşımı (ms)" onChange={(e) => setForm((f) => ({ ...f, statement_timeout_ms: Number(e.target.value) }))} type="number" value={form.statement_timeout_ms} />
            <TextField label="Ek bağlantı parametreleri (JSON)" minRows={2} multiline onChange={(e) => setConnectionParameters(e.target.value)} value={connectionParameters} />
            {createError ? <Alert severity="error">{createError}</Alert> : null}
          </Box></DialogContent>
          <DialogActions><Button disabled={createLoading} onClick={() => setCreateOpen(false)}>İptal</Button><Button disabled={createLoading || !form.name.trim() || !form.host.trim() || !form.database.trim() || !form.schema.trim() || !form.secret_reference.trim()} onClick={() => void submitCreate()} variant="contained">Kaydet</Button></DialogActions>
        </Dialog>

        <Dialog fullWidth maxWidth="xs" onClose={() => setPassivationSource(null)} open={passivationSource !== null}>
          <DialogTitle>Veri kaynağını pasifleştir</DialogTitle>
          <DialogContent><TextField autoFocus fullWidth helperText="Audit kaydında kullanılacak zorunlu gerekçe kodu" label="Gerekçe kodu" onChange={(e) => setPassivationReason(e.target.value)} required value={passivationReason} /></DialogContent>
          <DialogActions><Button onClick={() => setPassivationSource(null)}>İptal</Button><Button color="warning" disabled={!passivationReason.trim()} onClick={() => void submitPassivation()} variant="contained">Pasifleştir</Button></DialogActions>
        </Dialog>

        <Dialog fullWidth maxWidth="xs" onClose={() => setDecision(null)} open={decision !== null}>
          <DialogTitle>{decision?.value === "APPROVE" ? "Aktivasyon talebini onayla" : "Aktivasyon talebini reddet"}</DialogTitle>
          <DialogContent><TextField autoFocus fullWidth label="Karar gerekçe kodu" onChange={(e) => setDecisionReason(e.target.value)} required value={decisionReason} /></DialogContent>
          <DialogActions><Button onClick={() => setDecision(null)}>İptal</Button><Button disabled={!decisionReason.trim() || !decision?.item.pendingActivationRequestId} onClick={() => void submitDecision()} variant="contained">Kararı gönder</Button></DialogActions>
        </Dialog>
      </Box>
    </AppShell>
  );
}
