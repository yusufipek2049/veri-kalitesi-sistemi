import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  Paper,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { FileSearch, RefreshCw } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens } from "../theme/tokens";
import { ProfilingApiError, fetchDriftJudgment, fetchProfileSnapshotDetail, fetchProfileSnapshots } from "./api";
import {
  driftJudgmentFromApi,
  snapshotDetailFromApi,
  snapshotListItemFromApi,
  syntheticSnapshotDetail,
  syntheticSnapshots,
  type DriftJudgment,
  type ProfileSnapshotDetail,
  type ProfileSnapshotListItem,
  type ProfilingState,
} from "./model";

interface ProfilingPageProps {
  state?: ProfilingState;
  snapshots?: ProfileSnapshotListItem[];
  selectedSnapshot?: ProfileSnapshotDetail | null;
  driftJudgment?: DriftJudgment | null;
  correlationId?: string;
  limit?: number;
  onRefresh?: () => void;
  onSelectSnapshot?: (profileId: string) => void;
}

function statusTone(status: string): "success" | "critical" | "warning" | "unknown" {
  if (status === "COMPLETED") return "success";
  if (status === "TECHNICAL_ERROR") return "critical";
  if (status === "NO_DATA") return "warning";
  return "unknown";
}

function driftStatusTone(status: string): "success" | "critical" | "warning" | "unknown" {
  if (status === "COMPLETED") return "success";
  if (status === "CONFIGURATION_ERROR" || status === "INCOMPATIBLE") return "critical";
  if (status === "INSUFFICIENT_HISTORY") return "warning";
  return "unknown";
}

function driftStatusLabel(status: string): string {
  switch (status) {
    case "COMPLETED":
      return "Tamamlandı";
    case "CONFIGURATION_ERROR":
      return "Yapılandırma Hatası";
    case "INSUFFICIENT_HISTORY":
      return "Yetersiz Geçmiş";
    case "INCOMPATIBLE":
      return "Uyumsuz Snapshot";
    default:
      return "Bilinmiyor";
  }
}

function isUnknownJudgment(status: string): boolean {
  return status !== "COMPLETED";
}

function SnapshotRow({
  item,
  isSelected,
  onSelect,
}: {
  item: ProfileSnapshotListItem;
  isSelected: boolean;
  onSelect: (profileId: string) => void;
}) {
  return (
    <TableRow
      hover
      onClick={() => onSelect(item.profileId)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(item.profileId);
        }
      }}
      tabIndex={0}
      role="button"
      aria-label={`Snapshot ${item.profileId} seç`}
      aria-selected={isSelected}
      sx={{ cursor: "pointer", bgcolor: isSelected ? "action.selected" : undefined }}
    >
      <TableCell>{item.profileId}</TableCell>
      <TableCell>{item.method}</TableCell>
      <TableCell>
        <StatusBadge tone={statusTone(item.status)} label={item.status} />
      </TableCell>
      <TableCell>{item.durationMs} ms</TableCell>
      <TableCell>{new Date(item.finishedAt).toLocaleString("tr-TR")}</TableCell>
    </TableRow>
  );
}

function MetricsTable({ metrics }: { metrics: Record<string, unknown> }) {
  const entries = useMemo(() => Object.entries(metrics), [metrics]);
  if (entries.length === 0) {
    return <Typography variant="body2">Metrik bulunamadı.</Typography>;
  }
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small" aria-label="Profil metrikleri">
        <TableHead>
          <TableRow>
            <TableCell sx={{ fontWeight: 700 }}>Alan</TableCell>
            <TableCell sx={{ fontWeight: 700 }}>Değer</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {entries.map(([key, value]) => (
            <TableRow key={key}>
              <TableCell>{key}</TableCell>
              <TableCell>
                {typeof value === "object" && value !== null ? (
                  <pre style={{ margin: 0, fontSize: "0.75rem" }}>
                    {JSON.stringify(value, null, 2)}
                  </pre>
                ) : (
                  String(value)
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

function DriftSignalsTable({ judgment }: { judgment: DriftJudgment }) {
  if (isUnknownJudgment(judgment.status)) {
    return (
      <Alert severity={judgment.status === "INSUFFICIENT_HISTORY" ? "warning" : "error"}>
        <Typography variant="body2">{judgment.message}</Typography>
        {judgment.result.configuration_error && (
          <Typography variant="caption" sx={{ mt: 1, display: "block" }}>
            Gerekçe: {judgment.result.configuration_error}
          </Typography>
        )}
      </Alert>
    );
  }

  const signals = judgment.result.signals ?? [];
  if (signals.length === 0) {
    return <Typography variant="body2">Drift sinyali bulunamadı.</Typography>;
  }

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small" aria-label="Drift sinyalleri">
        <TableHead>
          <TableRow>
            <TableCell sx={{ fontWeight: 700 }}>Sinyal Türü</TableCell>
            <TableCell sx={{ fontWeight: 700 }}>Alan</TableCell>
            <TableCell sx={{ fontWeight: 700 }}>Eşik</TableCell>
            <TableCell sx={{ fontWeight: 700 }}>Gerçek Değer</TableCell>
            <TableCell sx={{ fontWeight: 700 }}>Durum</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {signals.map((signal, idx) => (
            <TableRow key={idx}>
              <TableCell>{signal.kind}</TableCell>
              <TableCell>{signal.field ?? "-"}</TableCell>
              <TableCell>{signal.threshold ?? "-"}</TableCell>
              <TableCell>{signal.actual_value ?? "-"}</TableCell>
              <TableCell>
                <StatusBadge
                  tone={signal.breached ? "critical" : "success"}
                  label={signal.breached ? "Aşıldı" : "Normal"}
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

export function ProfilingPage({
  state = "loading",
  snapshots = syntheticSnapshots,
  selectedSnapshot,
  driftJudgment,
  correlationId,
  limit,
  onRefresh,
  onSelectSnapshot,
}: ProfilingPageProps) {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [datasetId, setDatasetId] = useState(searchParams.get("dataset_id") ?? "");

  const selectedProfileId = searchParams.get("profile_id") ?? undefined;
  const invalidProfileId = searchParams.has("profile_id") && !searchParams.get("profile_id");

  const handleSelectSnapshot = useCallback(
    (profileId: string) => {
      const params = new URLSearchParams(searchParams);
      params.set("profile_id", profileId);
      navigate({ search: params.toString() }, { replace: true });
      onSelectSnapshot?.(profileId);
    },
    [navigate, searchParams, onSelectSnapshot],
  );

  const isLoading = state === "loading";
  const isEmpty = state === "empty";
  const isError = state === "error";
  const isUnauthorized = state === "unauthorized";

  return (
    <AppShell currentPage="Profiller">
      <Box sx={(theme) => ({ margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 4 } })}>
        <Box sx={{ alignItems: "center", display: "flex", justifyContent: "space-between", mb: 3 }}>
          <Box sx={{ alignItems: "center", display: "flex", gap: 2 }}>
            <FileSearch aria-hidden="true" size={28} />
            <Typography component="h1" variant="h5" sx={{ fontWeight: 700, m: 0 }}>
              Profil Snapshotları
            </Typography>
          </Box>
          {onRefresh && (
            <Chip
              icon={<RefreshCw size={16} />}
              label="Yenile"
              onClick={onRefresh}
              variant="outlined"
            />
          )}
        </Box>

        {isUnauthorized && (
          <Alert severity="warning" sx={{ mb: 3 }}>
            Bu görünüm için yetkiniz yok.
          </Alert>
        )}

        {isError && (
          <Alert severity="error" sx={{ mb: 3 }}>
            Profil verileri yüklenemedi.
            {correlationId && ` İzleme kodu: ${correlationId}`}
          </Alert>
        )}

        <Box sx={{ mb: 3 }}>
          <TextField
            label="Dataset ID"
            value={datasetId}
            onChange={(e) => setDatasetId(e.target.value)}
            size="small"
            fullWidth
            sx={{ maxWidth: 400 }}
            aria-label="Dataset kimliği"
          />
        </Box>

        {isLoading ? (
          <Skeleton height={200} />
        ) : isEmpty ? (
          <Alert severity="info">Bu dataset için profil snapshot bulunamadı.</Alert>
        ) : (
          <TableContainer component={Paper} variant="outlined">
            <Table aria-label="Profil snapshot listesi">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>Profile ID</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Metot</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Durum</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Süre</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Tamamlanma</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {snapshots.map((snapshot) => (
                  <SnapshotRow
                    key={snapshot.profileId}
                    item={snapshot}
                    isSelected={snapshot.profileId === selectedProfileId}
                    onSelect={handleSelectSnapshot}
                  />
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {limit !== undefined && (
          <Typography variant="caption" sx={{ mt: 1, display: "block" }}>
            Gösterilen: {snapshots.length} / {limit}
          </Typography>
        )}

        {invalidProfileId && (
          <Alert severity="warning" sx={{ mt: 3 }}>
            Geçersiz profil kimliği parametresi.
          </Alert>
        )}

        {selectedSnapshot && (
          <Box sx={{ mt: 4 }}>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
              Snapshot Detayı: {selectedSnapshot.profileId}
            </Typography>
            <Box sx={{ display: "flex", gap: 2, mb: 2, flexWrap: "wrap" }}>
              <Chip label={`Metot: ${selectedSnapshot.method}`} size="small" />
              <StatusBadge tone={statusTone(selectedSnapshot.status)} label={selectedSnapshot.status} />
              {selectedSnapshot.sampleRatio !== null && (
                <Chip label={`Örneklem: ${(selectedSnapshot.sampleRatio * 100).toFixed(0)}%`} size="small" />
              )}
              <Chip label={`Süre: ${selectedSnapshot.durationMs} ms`} size="small" />
            </Box>
            {selectedSnapshot.metrics.profile_contract != null && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                  Sözleşme Bilgisi
                </Typography>
                <MetricsTable
                  metrics={selectedSnapshot.metrics.profile_contract as Record<string, unknown>}
                />
              </Box>
            )}
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                Tüm Metrikler
              </Typography>
              <MetricsTable metrics={selectedSnapshot.metrics} />
            </Box>
          </Box>
        )}

        {driftJudgment && (
          <Box sx={{ mt: 4 }}>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
              Drift Hükmü
            </Typography>
            <Box sx={{ display: "flex", gap: 2, mb: 2, flexWrap: "wrap" }}>
              <StatusBadge
                tone={driftStatusTone(driftJudgment.status)}
                label={driftStatusLabel(driftJudgment.status)}
              />
              {driftJudgment.policyVersion && (
                <Chip label={`Politika: ${driftJudgment.policyVersion}`} size="small" />
              )}
              {driftJudgment.anomalyCandidate !== null && (
                <Chip
                  label={driftJudgment.anomalyCandidate ? "Anormal Aday" : "Normal"}
                  size="small"
                  color={driftJudgment.anomalyCandidate ? "warning" : "default"}
                />
              )}
            </Box>
            {isUnknownJudgment(driftJudgment.status) && (
              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  Bu snapshot için drift hükmü üretilemedi. Bu bir kalite sorunu değil,
                  politika veya geçmiş eksikliğinden kaynaklanır.
                </Typography>
              </Alert>
            )}
            <DriftSignalsTable judgment={driftJudgment} />
          </Box>
        )}
      </Box>
    </AppShell>
  );
}

export default ProfilingPage;
