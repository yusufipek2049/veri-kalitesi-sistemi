import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  Divider,
  Paper,
  Skeleton,
  Stack,
  Typography,
} from "@mui/material";
import {
  FileWarning,
  Lock,
  ServerCrash,
  ShieldOff,
} from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import {
  EvidenceApiError,
  fetchGovernanceProjection,
  fetchInvestigationEvidence,
  fetchLineageSnapshot,
} from "./api";
import {
  evidenceComponentValueText,
  governanceProjectionFromApi,
  investigationEvidenceFromApi,
  isHypothesisSnapshotKind,
  lineageSnapshotFromApi,
  sourceClassLabel,
  type EvidenceComponent,
  type EvidenceSourceClass,
  type GovernanceProjection,
  type InvestigationEvidence,
  type LineageSnapshot,
} from "./model";

export type InvestigationState =
  | "loading"
  | "ready"
  | "error"
  | "unauthorized"
  | "unavailable"
  | "not-found";

interface InvestigationData {
  snapshot: LineageSnapshot | null;
  projection: GovernanceProjection | null;
  evidence: InvestigationEvidence | null;
  correlationId?: string;
}

export interface InvestigationPageProps {
  assetRef: string;
  snapshotId?: string;
  issueId?: string;
  state?: InvestigationState;
  data?: InvestigationData;
  correlationId?: string;
  onRefresh?: () => void;
}

function sourceClassTone(
  sourceClass: EvidenceSourceClass,
): "success" | "warning" | "unknown" {
  const tones: Record<EvidenceSourceClass, "success" | "warning" | "unknown"> = {
    Observed: "success",
    Calculated: "warning",
    Estimated: "warning",
    Unknown: "unknown",
  };
  return tones[sourceClass];
}

function SourceClassChip({ label, sourceClass }: { label: string; sourceClass: EvidenceSourceClass }) {
  return (
    <Stack direction="row" sx={{ alignItems: "center", gap: 1 }}>
      <Typography color="text.secondary" variant="body2">{label}</Typography>
      <StatusBadge label={sourceClassLabel(sourceClass)} tone={sourceClassTone(sourceClass)} />
    </Stack>
  );
}

function GovernanceSection({ projection }: { projection: GovernanceProjection }) {
  return (
    <Paper sx={{ p: 3 }} variant="outlined">
      <Typography gutterBottom variant="h6">Yönetişim Projeksiyonu</Typography>
      <Stack sx={{ gap: 2 }}>
        <Stack direction="row" sx={{ alignItems: "center", gap: 1 }}>
          <Typography color="text.secondary" variant="body2">Varlık</Typography>
          <Typography variant="body2">{projection.assetRef}</Typography>
        </Stack>
        <Stack direction="row" sx={{ alignItems: "center", gap: 1 }}>
          <Typography color="text.secondary" variant="body2">Profil durumu</Typography>
          <Chip label={projection.governanceProfileStatus} size="small" variant="outlined" />
        </Stack>
        {projection.governanceVersion ? (
          <Stack direction="row" sx={{ alignItems: "center", gap: 1 }}>
            <Typography color="text.secondary" variant="body2">Sürüm</Typography>
            <Typography variant="body2">{projection.governanceVersion}</Typography>
          </Stack>
        ) : null}
        <SourceClassChip label="Kritik varlık" sourceClass={projection.criticalAssetStatus} />
        <SourceClassChip label="Risk durumu" sourceClass={projection.riskStatus} />
        <SourceClassChip label="SLA durumu" sourceClass={projection.slaStatus} />
        {projection.governanceReasonCodes.length ? (
          <Box>
            <Typography color="text.secondary" gutterBottom variant="body2">Gerekçe kodları</Typography>
            <Stack direction="row" sx={{ flexWrap: "wrap", gap: 0.5 }}>
              {projection.governanceReasonCodes.map((code) => (
                <Chip key={code} label={code} size="small" variant="outlined" />
              ))}
            </Stack>
          </Box>
        ) : null}
      </Stack>
    </Paper>
  );
}

function SnapshotSection({ snapshot }: { snapshot: LineageSnapshot }) {
  const isHypothesis = isHypothesisSnapshotKind(snapshot.snapshotKind);
  return (
    <Paper sx={{ p: 3 }} variant="outlined">
      <Stack direction="row" sx={{ alignItems: "center", gap: 1, mb: 2 }}>
        <Typography variant="h6">Lineage Kanıtı</Typography>
        {isHypothesis ? (
          <Chip color="warning" label="Hipotez" size="small" />
        ) : null}
      </Stack>
      <Stack sx={{ gap: 2 }}>
        <Stack direction="row" sx={{ alignItems: "center", gap: 1 }}>
          <Typography color="text.secondary" variant="body2">Tür</Typography>
          <Chip label={snapshot.snapshotKind} size="small" variant="outlined" />
        </Stack>
        <Stack direction="row" sx={{ alignItems: "center", gap: 1 }}>
          <Typography color="text.secondary" variant="body2">Konu</Typography>
          <Typography variant="body2">{snapshot.subjectRef}</Typography>
        </Stack>
        <Stack direction="row" sx={{ alignItems: "center", gap: 1 }}>
          <Typography color="text.secondary" variant="body2">Sürüm</Typography>
          <Typography variant="body2">{snapshot.versionLabel}</Typography>
        </Stack>
        <Stack direction="row" sx={{ alignItems: "center", gap: 1 }}>
          <Typography color="text.secondary" variant="body2">Digest</Typography>
          <Typography sx={{ fontFamily: "monospace" }} variant="body2">{snapshot.digest}</Typography>
        </Stack>
        <Stack direction="row" sx={{ alignItems: "center", gap: 1 }}>
          <Typography color="text.secondary" variant="body2">Oluşturulma</Typography>
          <Typography variant="body2">{snapshot.createdAt}</Typography>
        </Stack>
      </Stack>
    </Paper>
  );
}

const MAX_MASKED_SAMPLES_VISIBLE = 10;
const MAX_SIMILAR_HISTORY_VISIBLE = 5;

function EvidenceComponentRow({
  label,
  component,
  isMasked,
  isBounded,
  maxItems,
  isHypothesis,
}: {
  label: string;
  component: EvidenceComponent;
  isMasked?: boolean;
  isBounded?: boolean;
  maxItems?: number;
  isHypothesis?: boolean;
}) {
  const isUnknown = component.source === "Unknown";
  const valueText = evidenceComponentValueText(component);
  const isArray = Array.isArray(component.value);
  const arrayItems = isArray ? (component.value as Array<unknown>) : null;
  const hasMore = isBounded && arrayItems !== null && maxItems !== undefined && arrayItems.length > maxItems;
  const displayItems = hasMore && maxItems !== undefined ? arrayItems!.slice(0, maxItems) : arrayItems;

  return (
    <Box component="section" aria-label={label}>
      <Stack direction="row" sx={{ alignItems: "center", gap: 1, mb: 0.5 }}>
        <Typography color="text.secondary" variant="body2">{label}</Typography>
        <SourceClassChip label="Kaynak" sourceClass={component.source} />
        {isMasked ? <Chip label="Maskeli" size="small" variant="outlined" /> : null}
        {isHypothesis ? <Chip color="warning" label="Hipotez" size="small" /> : null}
      </Stack>
      {isUnknown ? (
        <Alert severity="info" variant="outlined">
          <Typography variant="body2">
            Bu bileşen için kanıt mevcut değildir. Değer bilinmemektedir;
            boş, sıfır veya varsayılan olarak yorumlanmamalıdır.
          </Typography>
        </Alert>
      ) : isArray && displayItems !== null ? (
        <Box>
          <Stack sx={{ gap: 0.5 }}>
            {displayItems.map((item, index) => (
              <Typography
                key={index}
                sx={{ fontFamily: isMasked ? "monospace" : undefined }}
                variant="body2"
              >
                {String(item)}
              </Typography>
            ))}
          </Stack>
          {hasMore ? (
            <Typography color="text.secondary" sx={{ mt: 0.5 }} variant="caption">
              Liste sınırlı gösteriliyor (ilk {maxItems} kayıt).
            </Typography>
          ) : null}
        </Box>
      ) : (
        <Typography
          sx={{ fontFamily: isMasked ? "monospace" : undefined, whiteSpace: "pre-line" }}
          variant="body2"
        >
          {valueText}
        </Typography>
      )}
      {component.references.length > 0 ? (
        <Stack direction="row" sx={{ flexWrap: "wrap", gap: 0.5, mt: 0.5 }}>
          {component.references.map((ref) => (
            <Chip key={ref} label={ref} size="small" variant="outlined" />
          ))}
        </Stack>
      ) : null}
    </Box>
  );
}

function EvidenceSection({ evidence }: { evidence: InvestigationEvidence }) {
  const maskedArray = Array.isArray(evidence.maskedSamples.value)
    ? (evidence.maskedSamples.value as Array<unknown>)
    : null;
  const maskedCount = maskedArray ? maskedArray.length : 0;
  const similarArray = Array.isArray(evidence.similarHistory.value)
    ? (evidence.similarHistory.value as Array<unknown>)
    : null;
  const similarCount = similarArray ? similarArray.length : 0;

  return (
    <Paper sx={{ p: 3 }} variant="outlined">
      <Typography gutterBottom variant="h6">İnceleme Kanıtı</Typography>
      <Stack sx={{ gap: 3 }}>
        <EvidenceComponentRow
          component={evidence.ruleDescription}
          label="Kural / sorgu açıklaması"
        />
        <Divider aria-hidden="true" />
        <EvidenceComponentRow
          component={evidence.expectedSummary}
          label="Beklenen değer"
        />
        <Divider aria-hidden="true" />
        <EvidenceComponentRow
          component={evidence.actualSummary}
          label="Gerçekleşen değer"
        />
        <Divider aria-hidden="true" />
        <EvidenceComponentRow
          component={evidence.maskedSamples}
          isBounded
          isMasked
          label={`Maskeli kötü örnek${maskedCount > 0 ? ` (${maskedCount} kayıt)` : ""}`}
          maxItems={MAX_MASKED_SAMPLES_VISIBLE}
        />
        <Divider aria-hidden="true" />
        <EvidenceComponentRow
          component={evidence.similarHistory}
          isBounded
          label={`Benzer geçmiş${similarCount > 0 ? ` (${similarCount} kayıt)` : ""}`}
          maxItems={MAX_SIMILAR_HISTORY_VISIBLE}
        />
        <Divider aria-hidden="true" />
        <EvidenceComponentRow
          component={evidence.recommendation}
          isHypothesis
          label="Kaynaklı öneri"
        />
        <Divider aria-hidden="true" />
        <Stack sx={{ gap: 1 }}>
          <Typography color="text.secondary" variant="body2">Kanıt referansları</Typography>
          <Stack direction="row" sx={{ flexWrap: "wrap", gap: 0.5 }}>
            {evidence.ruleVersionId ? (
              <Chip label={`Kural sürümü: ${evidence.ruleVersionId}`} size="small" variant="outlined" />
            ) : null}
            {evidence.irVersion ? (
              <Chip label={`IR sürümü: ${evidence.irVersion}`} size="small" variant="outlined" />
            ) : null}
            {evidence.evidenceFingerprint ? (
              <Chip label={`Parmak izi: ${evidence.evidenceFingerprint}`} size="small" variant="outlined" />
            ) : null}
            {evidence.evidenceQueryReference ? (
              <Chip label={`Sorgu: ${evidence.evidenceQueryReference}`} size="small" variant="outlined" />
            ) : null}
            {evidence.evidencePlanReference ? (
              <Chip label={`Plan: ${evidence.evidencePlanReference}`} size="small" variant="outlined" />
            ) : null}
            <Chip label={`Politika sürümü: ${evidence.authorizationPolicyVersion}`} size="small" variant="outlined" />
          </Stack>
        </Stack>
      </Stack>
    </Paper>
  );
}

function ErrorBanner({ state, correlationId }: { state: InvestigationState; correlationId?: string }) {
  if (state === "unauthorized") {
    return (
      <Alert icon={<ShieldOff aria-hidden="true" />} severity="warning">
        <Typography sx={{ fontWeight: 700 }}>Erişim reddedildi</Typography>
        <Typography variant="body2">
          Bu kanıt kapsamına erişim yetkiniz yok.
          {correlationId ? ` İzleme kodu: ${correlationId}.` : null}
        </Typography>
      </Alert>
    );
  }
  if (state === "unavailable") {
    return (
      <Alert icon={<ServerCrash aria-hidden="true" />} severity="info">
        <Typography sx={{ fontWeight: 700 }}>Kanıt hizmeti kullanılamıyor</Typography>
        <Typography variant="body2">
          Lineage ve yönetişim kanıt deposu şu anda erişilebilir değil.
          Kısmi veri kanıt olarak sunulmaz.
          {correlationId ? ` İzleme kodu: ${correlationId}.` : null}
        </Typography>
      </Alert>
    );
  }
  if (state === "not-found") {
    return (
      <Alert icon={<FileWarning aria-hidden="true" />} severity="info">
        <Typography sx={{ fontWeight: 700 }}>Kanıt bulunamadı</Typography>
        <Typography variant="body2">
          İstenen kanıt snapshot&apos;ı mevcut değil.
          {correlationId ? ` İzleme kodu: ${correlationId}.` : null}
        </Typography>
      </Alert>
    );
  }
  return (
    <Alert icon={<Lock aria-hidden="true" />} severity="error">
      <Typography sx={{ fontWeight: 700 }}>Kanıt yüklenemedi</Typography>
      <Typography variant="body2">
        Beklenmeyen bir hata oluştu. Yeniden deneyin.
        {correlationId ? ` İzleme kodu: ${correlationId}.` : null}
      </Typography>
    </Alert>
  );
}

export function InvestigationPage({
  assetRef,
  snapshotId,
  issueId,
  state: externalState,
  data,
  correlationId: externalCorrelationId,
  onRefresh,
}: InvestigationPageProps) {
  const [internalState, setInternalState] = useState<InvestigationState>("loading");
  const [internalData, setInternalData] = useState<InvestigationData>({ snapshot: null, projection: null, evidence: null });
  const [internalCorrelationId, setInternalCorrelationId] = useState<string>();

  const load = useCallback(async (signal?: AbortSignal) => {
    if (externalState) return;
    setInternalState("loading");
    try {
      const [snapshotResponse, projectionResponse] = await Promise.all([
        snapshotId ? fetchLineageSnapshot(snapshotId, signal) : Promise.resolve(null),
        fetchGovernanceProjection(assetRef, signal),
      ]);
      const nextData: InvestigationData = {
        snapshot: snapshotResponse ? lineageSnapshotFromApi(snapshotResponse) : null,
        projection: governanceProjectionFromApi(projectionResponse),
        evidence: null,
      };
      setInternalData(nextData);
      setInternalCorrelationId(projectionResponse.correlation_id);
      setInternalState("ready");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof EvidenceApiError) {
        setInternalCorrelationId(error.correlationId);
        const stateMap: Record<EvidenceApiError["kind"], InvestigationState> = {
          unauthorized: "unauthorized",
          "not-found": "not-found",
          unavailable: "unavailable",
          technical: "error",
        };
        setInternalState(stateMap[error.kind]);
      } else {
        setInternalState("error");
      }
    }
  }, [assetRef, snapshotId, externalState]);

  const loadEvidence = useCallback(async (signal?: AbortSignal) => {
    if (!issueId) return;
    try {
      const evidenceResponse = await fetchInvestigationEvidence(issueId, signal);
      setInternalData((prev) => ({
        ...prev,
        evidence: investigationEvidenceFromApi(evidenceResponse),
      }));
    } catch {
      /* Evidence is supplementary; page stays ready without it. */
    }
  }, [issueId]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  useEffect(() => {
    const controller = new AbortController();
    void loadEvidence(controller.signal);
    return () => controller.abort();
  }, [loadEvidence]);

  const activeState = externalState ?? internalState;
  const activeData = data ?? internalData;
  const activeCorrelationId = externalCorrelationId ?? internalCorrelationId;

  return (
    <AppShell currentPage="Kanıt İnceleme">
      <Box sx={(theme) => ({ margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 6 } })}>
        <Stack sx={{ gap: 3 }}>
          <Stack direction="row" sx={{ alignItems: "center", justifyContent: "space-between" }}>
            <Typography variant="h5">Kanıt İnceleme</Typography>
            {onRefresh ? (
              <Chip
                clickable
                label="Yenile"
                size="small"
                onClick={onRefresh}
              />
            ) : null}
          </Stack>

          {activeState === "ready" || activeState === "loading" ? (
            <Typography color="text.secondary" variant="body2">
              Varlık: <strong>{assetRef}</strong>
              {snapshotId ? ` · Snapshot: ${snapshotId}` : null}
            </Typography>
          ) : null}

          {activeCorrelationId ? (
            <Typography color="text.secondary" variant="caption">
              İzleme kodu: {activeCorrelationId}
            </Typography>
          ) : null}

          {activeState === "loading" ? (
            <Stack sx={{ gap: 2 }}>
              <Skeleton height={120} variant="rounded" />
              <Skeleton height={180} variant="rounded" />
            </Stack>
          ) : activeState !== "ready" ? (
            <ErrorBanner correlationId={activeCorrelationId} state={activeState} />
          ) : (
            <Stack sx={{ gap: 3 }}>
              {activeData.evidence ? (
                <EvidenceSection evidence={activeData.evidence} />
              ) : null}
              {activeData.projection ? (
                <GovernanceSection projection={activeData.projection} />
              ) : (
                <Alert severity="info">
                  <Typography sx={{ fontWeight: 700 }}>Yönetişim kanıtı yok</Typography>
                  <Typography variant="body2">
                    Bu varlık için yönetişim projeksiyonu Unknown olarak döndü.
                    Tahmin veya boş-varsayılan üretilmez.
                  </Typography>
                </Alert>
              )}
              {activeData.snapshot ? (
                <SnapshotSection snapshot={activeData.snapshot} />
              ) : snapshotId ? null : (
                <Alert severity="info">
                  <Typography variant="body2">
                    Lineage snapshot belirtilmedi. Yalnızca yönetişim projeksiyonu gösteriliyor.
                  </Typography>
                </Alert>
              )}
            </Stack>
          )}
        </Stack>
      </Box>
    </AppShell>
  );
}
