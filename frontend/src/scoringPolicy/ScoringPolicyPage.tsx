import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { AppShell } from "../components/AppShell";
import { listCatalogDatasets } from "../catalog/api";
import type { CatalogDatasetListApiResponse } from "../catalog/model";
import { useDevelopmentUser } from "../development/UserContext";
import {
  decideScoringConfigurationApproval,
  fetchScoringConfigurations,
  ScoringPolicyApiError,
  submitScoringConfiguration,
  type ScoringConfigurationApi,
  type ScoringConfigurationApprovalApi,
  type ScoringConfigurationEntryApi,
  type ScoringConfigurationListApiResponse,
} from "./api";

type ScoringPolicyState = "loading" | "normal" | "error" | "unauthorized";
type DatasetOption = CatalogDatasetListApiResponse["items"][number];

const scoringMakerRoles = new Set(["DATA_STEWARD", "DATA_GOVERNANCE_SPECIALIST"]);
const scoringCheckerRoles = new Set(["DATA_OWNER"]);

function splitRoles(roles: string | undefined): string[] {
  return roles?.split(/\s*\/\s*/) ?? [];
}

export function canProposeScoringConfiguration(roles: string | undefined): boolean {
  return splitRoles(roles).some((role) => scoringMakerRoles.has(role));
}

export function canDecideScoringConfiguration(roles: string | undefined): boolean {
  return splitRoles(roles).some((role) => scoringCheckerRoles.has(role));
}

function formatDateTime(value: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("tr-TR");
}

function statusChip(status: string) {
  const color = status === "APPROVED" ? "success" : status === "REJECTED" ? "error" : "warning";
  const label =
    status === "APPROVED" ? "Onaylandı" : status === "REJECTED" ? "Reddedildi" : "Bekliyor";
  return <Chip color={color} label={label} size="small" />;
}

function ActiveConfigurationCard({ configuration }: { configuration: ScoringConfigurationApi | null }) {
  return (
    <Card>
      <CardContent>
        <Typography sx={{ fontWeight: 700, mb: 1 }} variant="h6">
          Aktif Konfigürasyon
        </Typography>
        {configuration ? (
          <Stack spacing={1}>
            <Typography>
              <strong>Sürüm:</strong> {configuration.version}
            </Typography>
            <Typography>
              <strong>Eşik seti:</strong> {configuration.threshold_set.version} — kritik &lt;{" "}
              {configuration.threshold_set.critical_upper_exclusive}, riskli &lt;{" "}
              {configuration.threshold_set.risky_upper_exclusive}, kabul edilebilir &lt;{" "}
              {configuration.threshold_set.acceptable_upper_exclusive}
            </Typography>
            <Typography>
              <strong>Aktifleştirme:</strong> {formatDateTime(configuration.activated_at)} ·{" "}
              <strong>Oluşturan:</strong> {configuration.created_by}
            </Typography>
          </Stack>
        ) : (
          <Typography color="text.secondary">Aktif konfigürasyon bulunamadı.</Typography>
        )}
      </CardContent>
    </Card>
  );
}

interface PendingApprovalCardProps {
  approval: ScoringConfigurationApprovalApi | null;
  configuration: ScoringConfigurationApi | null;
  canDecide: boolean;
  busy: boolean;
  onDecision: (decision: "APPROVE" | "REJECT", reasonCode: string) => Promise<void>;
}

function PendingApprovalCard({ approval, configuration, canDecide, busy, onDecision }: PendingApprovalCardProps) {
  const [reasonCode, setReasonCode] = useState("");
  return (
    <Card>
      <CardContent>
        <Typography sx={{ fontWeight: 700, mb: 1 }} variant="h6">
          Bekleyen Onay
        </Typography>
        {approval ? (
          <Stack spacing={2}>
            <Typography>
              <strong>Konfigürasyon:</strong> {configuration?.version ?? "—"} ·{" "}
              <strong>Öneren:</strong> {approval.maker_actor_id} ·{" "}
              <strong>Talep:</strong> {formatDateTime(approval.requested_at)}
            </Typography>
            {canDecide ? (
              <Stack spacing={2} sx={{ maxWidth: 520 }}>
                <TextField
                  label="Gerekçe kodu"
                  onChange={(event) => setReasonCode(event.target.value)}
                  placeholder="SCORING.CONFIGURATION.REVIEWED"
                  size="small"
                  value={reasonCode}
                />
                <Stack direction="row" spacing={2}>
                  <Button
                    color="success"
                    disabled={busy || !reasonCode.trim()}
                    onClick={() => void onDecision("APPROVE", reasonCode.trim())}
                    variant="contained"
                  >
                    Onayla ve aktifleştir
                  </Button>
                  <Button
                    color="error"
                    disabled={busy || !reasonCode.trim()}
                    onClick={() => void onDecision("REJECT", reasonCode.trim())}
                    variant="outlined"
                  >
                    Reddet
                  </Button>
                </Stack>
              </Stack>
            ) : (
              <Typography color="text.secondary" variant="body2">
                Karar vermek için DATA_OWNER rolü gerekir.
              </Typography>
            )}
          </Stack>
        ) : (
          <Typography color="text.secondary">Bekleyen onay yok.</Typography>
        )}
      </CardContent>
    </Card>
  );
}

interface ProposalFormProps {
  activeConfiguration: ScoringConfigurationApi | null;
  hasPendingApproval: boolean;
  busy: boolean;
  datasets: DatasetOption[];
  onSubmit: (payload: {
    version: string;
    thresholdVersion: string;
    criticalUpper: string;
    riskyUpper: string;
    acceptableUpper: string;
    datasetId: string | null;
  }) => Promise<void>;
}

function ProposalForm({ activeConfiguration, hasPendingApproval, busy, datasets, onSubmit }: ProposalFormProps) {
  const [version, setVersion] = useState("");
  const [thresholdVersion, setThresholdVersion] = useState("");
  const [criticalUpper, setCriticalUpper] = useState("");
  const [riskyUpper, setRiskyUpper] = useState("");
  const [acceptableUpper, setAcceptableUpper] = useState("");
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);

  const handleSubmit = useCallback(async () => {
    await onSubmit({ version, thresholdVersion, criticalUpper, riskyUpper, acceptableUpper, datasetId: selectedDatasetId });
    setVersion("");
    setThresholdVersion("");
    setCriticalUpper("");
    setRiskyUpper("");
    setAcceptableUpper("");
    setSelectedDatasetId(null);
  }, [onSubmit, version, thresholdVersion, criticalUpper, riskyUpper, acceptableUpper, selectedDatasetId]);

  return (
    <Card>
      <CardContent>
        <Typography sx={{ fontWeight: 700, mb: 1 }} variant="h6">
          Yeni Konfigürasyon Öner
        </Typography>
        <Stack spacing={2} sx={{ maxWidth: 520 }}>
          <TextField
            label="Konfigürasyon sürümü"
            onChange={(event) => setVersion(event.target.value)}
            placeholder="SCORING_CFG_V2"
            required
            size="small"
            value={version}
          />
          <TextField
            helperText="Boş bırakılırsa aktif konfigürasyonun değerleri kullanılır."
            label="Eşik seti sürümü (isteğe bağlı)"
            onChange={(event) => setThresholdVersion(event.target.value)}
            size="small"
            value={thresholdVersion}
          />
          <Stack direction="row" spacing={2}>
            <TextField
              label="Kritik eşiği"
              onChange={(event) => setCriticalUpper(event.target.value)}
              placeholder={activeConfiguration?.threshold_set.critical_upper_exclusive ?? "50.00"}
              size="small"
              value={criticalUpper}
            />
            <TextField
              label="Riskli eşiği"
              onChange={(event) => setRiskyUpper(event.target.value)}
              placeholder={activeConfiguration?.threshold_set.risky_upper_exclusive ?? "75.00"}
              size="small"
              value={riskyUpper}
            />
            <TextField
              label="Kabul edilebilir eşiği"
              onChange={(event) => setAcceptableUpper(event.target.value)}
              placeholder={activeConfiguration?.threshold_set.acceptable_upper_exclusive ?? "90.00"}
              size="small"
              value={acceptableUpper}
            />
          </Stack>
          <Autocomplete
            getOptionLabel={(option) => option.name || option.dataset_id}
            onChange={(_event, value) => setSelectedDatasetId(value?.dataset_id ?? null)}
            options={datasets}
            renderInput={(params) => (
              <TextField
                {...params}
                helperText="Belirli bir dataset'e özel konfigürasyon için dataset seçin. Boş bırakılırsa global konfigürasyon olur."
                label="Dataset kapsamı (isteğe bağlı)"
                size="small"
              />
            )}
            size="small"
            value={datasets.find((d) => d.dataset_id === selectedDatasetId) ?? null}
          />
          <Button
            disabled={busy || !version.trim() || hasPendingApproval}
            onClick={() => void handleSubmit()}
            variant="contained"
          >
            Onaya gönder
          </Button>
          {hasPendingApproval && (
            <Typography color="text.secondary" variant="body2">
              Bekleyen bir onay varken yeni öneri gönderilemez.
            </Typography>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

function ConfigurationHistoryCard({ entries }: { entries: ScoringConfigurationEntryApi[] }) {
  return (
    <Card>
      <CardContent>
        <Typography sx={{ fontWeight: 700, mb: 1 }} variant="h6">
          Konfigürasyon Geçmişi
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Sürüm</TableCell>
              <TableCell>Kapsam</TableCell>
              <TableCell>Durum</TableCell>
              <TableCell>Eşik seti</TableCell>
              <TableCell>Oluşturan</TableCell>
              <TableCell>Oluşturma</TableCell>
              <TableCell>Onay durumu</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {entries.map((entry) => (
              <TableRow key={entry.configuration.configuration_id}>
                <TableCell>{entry.configuration.version}</TableCell>
                <TableCell>
                  {entry.configuration.dataset_id ? (
                    <Chip label={entry.configuration.dataset_id} size="small" variant="outlined" />
                  ) : (
                    <Chip label="Global" size="small" color="default" />
                  )}
                </TableCell>
                <TableCell>
                  {entry.configuration.is_active ? (
                    <Chip color="success" label="Aktif" size="small" />
                  ) : (
                    <Chip label="Pasif" size="small" variant="outlined" />
                  )}
                </TableCell>
                <TableCell>{entry.configuration.threshold_set.version}</TableCell>
                <TableCell>{entry.configuration.created_by}</TableCell>
                <TableCell>{formatDateTime(entry.configuration.created_at)}</TableCell>
                <TableCell>{entry.approval ? statusChip(entry.approval.status) : "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

export interface ProposalFormValues {
  version: string;
  thresholdVersion: string;
  criticalUpper: string;
  riskyUpper: string;
  acceptableUpper: string;
  datasetId: string | null;
}

function describeError(error: unknown): string {
  if (error instanceof ScoringPolicyApiError) return error.message;
  return "İşlem tamamlanamadı. Yeniden deneyin.";
}

function useScoringPolicy(datasetFilter: string | null) {
  const [state, setState] = useState<ScoringPolicyState>("loading");
  const [data, setData] = useState<ScoringConfigurationListApiResponse | null>(null);
  const [correlationId, setCorrelationId] = useState<string>();
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionInfo, setActionInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (signal?: AbortSignal) => {
    setState("loading");
    try {
      const response = await fetchScoringConfigurations(signal, datasetFilter ?? undefined);
      if (signal?.aborted) return;
      setData(response);
      setCorrelationId(response.correlation_id);
      setState("normal");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof ScoringPolicyApiError) {
        setCorrelationId(error.correlationId);
        setState(error.kind === "unauthorized" ? "unauthorized" : "error");
      } else {
        setState("error");
      }
    }
  }, [datasetFilter]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const handleSubmitProposal = useCallback(
    async (form: ProposalFormValues) => {
      setActionError(null);
      setActionInfo(null);
      setBusy(true);
      try {
        await submitScoringConfiguration({
          version: form.version.trim(),
          threshold_version: form.thresholdVersion.trim() || undefined,
          critical_upper_exclusive: form.criticalUpper.trim() || undefined,
          risky_upper_exclusive: form.riskyUpper.trim() || undefined,
          acceptable_upper_exclusive: form.acceptableUpper.trim() || undefined,
          dataset_id: form.datasetId,
        });
        setActionInfo("Konfigürasyon önerisi gönderildi ve onay bekliyor.");
        await load();
      } catch (error) {
        setActionError(describeError(error));
      } finally {
        setBusy(false);
      }
    },
    [load],
  );

  const handleDecision = useCallback(
    async (decision: "APPROVE" | "REJECT", reasonCode: string) => {
      if (!data?.pending_approval) return;
      setActionError(null);
      setActionInfo(null);
      setBusy(true);
      try {
        await decideScoringConfigurationApproval(data.pending_approval.approval_id, {
          decision,
          reason_code: reasonCode,
        });
        setActionInfo(
          decision === "APPROVE" ? "Öneri onaylandı ve konfigürasyon aktifleştirildi." : "Öneri reddedildi.",
        );
        await load();
      } catch (error) {
        setActionError(describeError(error));
      } finally {
        setBusy(false);
      }
    },
    [data, load],
  );

  return {
    actionError,
    actionInfo,
    busy,
    correlationId,
    data,
    handleDecision,
    handleSubmitProposal,
    load,
    state,
  };
}

function ScoringPolicyStatusView({
  correlationId,
  load,
  state,
}: {
  correlationId?: string;
  load: (signal?: AbortSignal) => Promise<void>;
  state: ScoringPolicyState;
}) {
  if (state === "loading") {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress aria-label="Yükleniyor" />
      </Box>
    );
  }
  if (state === "unauthorized") {
    return (
      <Alert severity="warning">
        <Typography sx={{ fontWeight: 700 }}>Bu görünüm için yetkiniz yok</Typography>
        <Typography variant="body2">
          Skorlama politikasını görüntülemek için kurumsal kapsam yetkisi gerekir.
          {correlationId ? ` İzleme kodu: ${correlationId}.` : ""}
        </Typography>
      </Alert>
    );
  }
  if (state === "error") {
    return (
      <Alert severity="error">
        <Typography>Skorlama politikası yüklenemedi.</Typography>
        <Button onClick={() => void load()}>Yeniden dene</Button>
      </Alert>
    );
  }
  return null;
}

function selectConfigurations(data: ScoringConfigurationListApiResponse | null) {
  const activeConfiguration =
    data?.items.find((entry) => entry.configuration.is_active)?.configuration ?? null;
  const pendingApproval = data?.pending_approval ?? null;
  const pendingConfiguration = pendingApproval
    ? data?.items.find(
        (entry) => entry.configuration.configuration_id === pendingApproval.configuration_id,
      )?.configuration ?? null
    : null;
  return { activeConfiguration, pendingApproval, pendingConfiguration };
}

export function ScoringPolicyPage() {
  const { currentUser } = useDevelopmentUser();
  const canPropose = canProposeScoringConfiguration(currentUser?.roles);
  const canDecide = canDecideScoringConfiguration(currentUser?.roles);
  const [datasetFilter, setDatasetFilter] = useState<string | null>(null);
  const [datasets, setDatasets] = useState<DatasetOption[]>([]);
  const policy = useScoringPolicy(datasetFilter);
  const { activeConfiguration, pendingApproval, pendingConfiguration } = selectConfigurations(policy.data);

  useEffect(() => {
    const controller = new AbortController();
    listCatalogDatasets(undefined, controller.signal)
      .then((response) => setDatasets(response.items))
      .catch(() => { /* catalog may be unavailable */ });
    return () => controller.abort();
  }, []);

  return (
    <AppShell currentPage="Skorlama Politikası">
      <Box sx={(theme) => ({ margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 2, md: 3 } })}>
        <Typography sx={{ fontWeight: 700, mb: 2 }} variant="h5">
          Skorlama Politikası
        </Typography>

        {policy.state !== "normal" && (
          <ScoringPolicyStatusView
            correlationId={policy.correlationId}
            load={policy.load}
            state={policy.state}
          />
        )}

        {policy.state === "normal" && policy.data && (
          <Stack spacing={3}>
            {policy.actionError && <Alert severity="error">{policy.actionError}</Alert>}
            {policy.actionInfo && <Alert severity="success">{policy.actionInfo}</Alert>}
            <ActiveConfigurationCard configuration={activeConfiguration} />
            <PendingApprovalCard
              approval={pendingApproval}
              busy={policy.busy}
              canDecide={canDecide}
              configuration={pendingConfiguration}
              onDecision={policy.handleDecision}
            />
            {canPropose && (
              <ProposalForm
                activeConfiguration={activeConfiguration}
                busy={policy.busy}
                datasets={datasets}
                hasPendingApproval={Boolean(pendingApproval)}
                onSubmit={policy.handleSubmitProposal}
              />
            )}
            <Card>
              <CardContent>
                <Typography sx={{ fontWeight: 700, mb: 1 }} variant="subtitle1">
                  Dataset Filtresi
                </Typography>
                <Autocomplete
                  clearText="Temizle"
                  getOptionLabel={(option) => option.name || option.dataset_id}
                  onChange={(_event, value) => setDatasetFilter(value?.dataset_id ?? null)}
                  options={datasets}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      helperText="Belirli bir dataset'e ait konfigürasyonları görmek için seçin."
                      label="Dataset filtresi (isteğe bağlı)"
                      size="small"
                    />
                  )}
                  size="small"
                  sx={{ maxWidth: 400 }}
                  value={datasets.find((d) => d.dataset_id === datasetFilter) ?? null}
                />
              </CardContent>
            </Card>
            <ConfigurationHistoryCard entries={policy.data.items} />
          </Stack>
        )}
      </Box>
    </AppShell>
  );
}
