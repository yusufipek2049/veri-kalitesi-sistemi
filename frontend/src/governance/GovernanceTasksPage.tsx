import { useState } from "react";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { Plus, RefreshCw } from "lucide-react";
import { AppShell } from "../components/AppShell";
import {
  governanceActionLabels,
  governanceDecisionReasonCodes,
  governanceFieldSensitivityReasonCodes,
  governanceMetadataReasonCodes,
  governanceOwnershipReasonCodes,
  governanceRemainingLabel,
  governanceRequestTypeLabels,
  governanceStatusLabels,
  governanceTargetHref,
  governanceViewLabels,
  governanceViews,
  governanceWithdrawReasonCodes,
  type GovernanceApprovalItem,
  type GovernanceState,
  type GovernanceView,
} from "./model";
import { CLASSIFICATION_OPTIONS } from "../catalog/model";
import { Link } from "react-router-dom";

interface GovernanceTasksPageProps {
  state?: GovernanceState;
  items: GovernanceApprovalItem[];
  view: GovernanceView;
  correlationId?: string;
  actionError?: string | null;
  datasets?: { id: string; name: string; namespace: string; ownerId?: string | null }[];
  ownerCandidates?: GovernanceOwnerCandidate[];
  onViewChange?: (view: GovernanceView) => void;
  onRefresh?: () => void;
  onDecide?: (approvalRequestId: string, decision: "APPROVE" | "REJECT", reasonCode: string) => Promise<void> | void;
  onWithdraw?: (approvalRequestId: string, reasonCode: string) => Promise<void> | void;
  onApply?: (approvalRequestId: string) => Promise<void> | void;
  onCreateRequest?: (payload: {
    requestType: string;
    objectId: string;
    reasonCode: string;
    newOwnerUserId?: string;
    proposedChanges?: Record<string, unknown>;
  }) => Promise<void> | void;
  loadFields?: (datasetId: string) => Promise<{ id: string; name: string }[]>;
}

export interface GovernanceOwnerCandidate {
  id: string;
  displayName: string;
  roles: string;
}

type CreateRequestKind = "OWNERSHIP" | "METADATA" | "FIELD_SENSITIVITY";

const createKindLabels: Record<CreateRequestKind, string> = {
  OWNERSHIP: "Sahiplik",
  METADATA: "Kritik metadata",
  FIELD_SENSITIVITY: "Alan hassasiyeti",
};

const criticalityOptions = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
const datasetStatusOptions = ["ACTIVE", "INACTIVE"];

const statusColors: Record<string, "warning" | "success" | "error" | "default" | "info"> = {
  PENDING: "warning",
  APPROVED: "success",
  REJECTED: "error",
  WITHDRAWN: "default",
  EXPIRED: "default",
  INVALIDATED: "info",
  APPLIED: "success",
  APPLICATION_FAILED: "error",
};

function formatDateTime(value: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "—" : parsed.toLocaleString("tr-TR");
}

function normalizedSearchText(value: string): string {
  return value
    .trim()
    .toLocaleLowerCase("tr-TR")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replaceAll("ı", "i");
}

export function filterGovernanceOwnerCandidates(
  candidates: GovernanceOwnerCandidate[],
  query: string,
): GovernanceOwnerCandidate[] {
  const normalizedQuery = normalizedSearchText(query);
  const ranked = candidates
    .map((candidate) => {
      const id = normalizedSearchText(candidate.id);
      const displayName = normalizedSearchText(candidate.displayName);
      const roles = normalizedSearchText(candidate.roles);
      const searchable = `${displayName} ${id} ${roles}`;
      if (normalizedQuery && !searchable.includes(normalizedQuery)) return null;

      let score = 4;
      if (!normalizedQuery) score = 3;
      else if (id === normalizedQuery || displayName === normalizedQuery) score = 0;
      else if (id.startsWith(normalizedQuery) || displayName.startsWith(normalizedQuery)) score = 1;
      else if (displayName.split(/\s+/).some((word) => word.startsWith(normalizedQuery))) score = 2;

      return { candidate, score };
    })
    .filter((entry): entry is { candidate: GovernanceOwnerCandidate; score: number } => entry !== null);

  ranked.sort(
    (left, right) =>
      left.score - right.score ||
      left.candidate.displayName.localeCompare(right.candidate.displayName, "tr"),
  );
  return ranked.slice(0, 5).map(({ candidate }) => candidate);
}

export function GovernanceTasksPage({
  state = "normal",
  items,
  view,
  correlationId,
  actionError = null,
  datasets = [],
  ownerCandidates = [],
  onViewChange,
  onRefresh,
  onDecide,
  onWithdraw,
  onApply,
  onCreateRequest,
  loadFields,
}: GovernanceTasksPageProps) {
  const now = new Date();
  const [decisionTarget, setDecisionTarget] = useState<GovernanceApprovalItem | null>(null);
  const [decision, setDecision] = useState<"APPROVE" | "REJECT">("APPROVE");
  const [decisionReason, setDecisionReason] = useState(governanceDecisionReasonCodes[0]);
  const [withdrawTarget, setWithdrawTarget] = useState<GovernanceApprovalItem | null>(null);
  const [withdrawReason, setWithdrawReason] = useState(governanceWithdrawReasonCodes[0]);
  const [detailTarget, setDetailTarget] = useState<GovernanceApprovalItem | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createKind, setCreateKind] = useState<CreateRequestKind>("OWNERSHIP");
  const [createDatasetId, setCreateDatasetId] = useState("");
  const [createOwner, setCreateOwner] = useState("");
  const [createReason, setCreateReason] = useState(governanceOwnershipReasonCodes[1]);
  const [createMetaAttribute, setCreateMetaAttribute] = useState<"criticality" | "status">("criticality");
  const [createMetaValue, setCreateMetaValue] = useState("CRITICAL");
  const [createFieldId, setCreateFieldId] = useState("");
  const [createFields, setCreateFields] = useState<{ id: string; name: string }[]>([]);
  const [createFieldsLoading, setCreateFieldsLoading] = useState(false);
  const [createSensitive, setCreateSensitive] = useState(true);
  const [createClassification, setCreateClassification] = useState("PERSONAL_DATA");

  const selectedDataset = datasets.find((candidate) => candidate.id === createDatasetId);
  const ownershipRequestType = selectedDataset?.ownerId ? "DATASET_OWNER_CHANGE" : "DATASET_OWNER_ASSIGN";
  const selectableOwnerCandidates = ownerCandidates.filter(
    (candidate) => candidate.id !== selectedDataset?.ownerId,
  );

  const handleKindChange = (kind: CreateRequestKind) => {
    setCreateKind(kind);
    if (kind === "OWNERSHIP") setCreateReason(governanceOwnershipReasonCodes[1]);
    if (kind === "METADATA") setCreateReason(governanceMetadataReasonCodes[0]);
    if (kind === "FIELD_SENSITIVITY") setCreateReason(governanceFieldSensitivityReasonCodes[0]);
  };

  const handleCreateDatasetChange = (datasetId: string) => {
    setCreateDatasetId(datasetId);
    setCreateOwner("");
    setCreateFieldId("");
    setCreateFields([]);
    if (!datasetId || !loadFields) return;
    setCreateFieldsLoading(true);
    loadFields(datasetId)
      .then((fields) => setCreateFields(fields))
      .catch(() => setCreateFields([]))
      .finally(() => setCreateFieldsLoading(false));
  };

  const createEnabled =
    createKind === "OWNERSHIP"
      ? Boolean(createDatasetId && createOwner.trim())
      : createKind === "METADATA"
        ? Boolean(createDatasetId)
        : Boolean(createDatasetId && createFieldId);

  const handleSubmitCreate = () => {
    if (!onCreateRequest) return;
    if (createKind === "OWNERSHIP") {
      void onCreateRequest({
        requestType: ownershipRequestType,
        objectId: createDatasetId,
        newOwnerUserId: createOwner.trim(),
        reasonCode: createReason,
      });
    } else if (createKind === "METADATA") {
      void onCreateRequest({
        requestType: "METADATA_CRITICAL_CHANGE",
        objectId: createDatasetId,
        proposedChanges: { [createMetaAttribute]: createMetaValue },
        reasonCode: createReason,
      });
    } else {
      void onCreateRequest({
        requestType: "FIELD_SENSITIVITY_MARK",
        objectId: createFieldId,
        proposedChanges: { is_sensitive: createSensitive, classification: createClassification },
        reasonCode: createReason,
      });
    }
    setCreateOpen(false);
  };

  return (
    <AppShell currentPage="Yönetişim Görevleri">
      <Box
        sx={(theme) => ({
          display: "grid",
          gap: 4,
          margin: "0 auto",
          maxWidth: theme.appLayout.contentMaxWidth,
          p: { xs: 3, md: 4, lg: 6 },
          width: "100%",
        })}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          sx={{ alignItems: { md: "center" }, gap: 2, justifyContent: "space-between" }}
        >
          <Box>
            <Typography component="h1" sx={{ fontWeight: 800 }} variant="h5">
              Yönetişim Görevleri
            </Typography>
            <Typography color="text.secondary" variant="body2">
              Maker-checker taleplerini onaylayın, izleyin ve denetleyin.
            </Typography>
          </Box>
          <Stack direction="row" sx={{ gap: 1 }}>
            {onCreateRequest ? (
              <Button onClick={() => setCreateOpen(true)} startIcon={<Plus size={16} />} variant="contained">
                Yönetişim Talebi
              </Button>
            ) : null}
            <Button
              disabled={state === "loading"}
              onClick={onRefresh}
              startIcon={<RefreshCw size={16} />}
              variant="outlined"
            >
              Yenile
            </Button>
          </Stack>
        </Stack>

        <Tabs
          aria-label="Yönetişim görünümleri"
          onChange={(_event, nextView: GovernanceView) => onViewChange?.(nextView)}
          scrollButtons="auto"
          value={view}
          variant="scrollable"
        >
          {governanceViews.map((candidate) => (
            <Tab key={candidate} label={governanceViewLabels[candidate]} value={candidate} />
          ))}
        </Tabs>

        {actionError ? <Alert severity="error">{actionError}</Alert> : null}

        {state === "loading" && (
          <Box aria-busy="true" sx={{ display: "grid", justifyItems: "center", py: 8 }}>
            <CircularProgress />
            <Typography color="text.secondary" sx={{ mt: 2 }} variant="body2">
              Talepler yükleniyor…
            </Typography>
          </Box>
        )}

        {state === "unauthorized" && (
          <Alert severity="warning">
            <Typography sx={{ fontWeight: 700 }}>Bu görünüm için yetkiniz yok</Typography>
            <Typography variant="body2">
              Yönetişim taleplerine erişim verilmedi.
              {correlationId ? ` İzleme kodu: ${correlationId}` : ""}
            </Typography>
          </Alert>
        )}

        {state === "error" && (
          <Alert severity="error">
            <Typography sx={{ fontWeight: 700 }}>Talepler yüklenemedi</Typography>
            <Typography variant="body2">
              Yeniden deneyin. Sorun devam ederse yöneticinize başvurun.
              {correlationId ? ` İzleme kodu: ${correlationId}` : ""}
            </Typography>
          </Alert>
        )}

        {state === "empty" && (
          <Alert severity="info">
            <Typography sx={{ fontWeight: 700 }}>{governanceViewLabels[view]} boş</Typography>
            <Typography variant="body2">Bu görünümde gösterilecek talep bulunmuyor.</Typography>
          </Alert>
        )}

        {state === "normal" && (
          <TableContainer>
            <Table aria-label="Yönetişim talepleri" size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Talep türü</TableCell>
                  <TableCell>Hedef nesne</TableCell>
                  <TableCell>Kapsam</TableCell>
                  <TableCell>Maker</TableCell>
                  <TableCell>Talep zamanı</TableCell>
                  <TableCell>Son karar</TableCell>
                  <TableCell>Durum</TableCell>
                  <TableCell>Kalan süre</TableCell>
                  <TableCell align="right">Kullanılabilir aksiyonlar</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.map((item) => (
                  <TableRow hover key={item.approvalRequestId}>
                    <TableCell>
                      <Typography sx={{ fontWeight: 600 }} variant="body2">
                        {governanceRequestTypeLabels[item.requestType] ?? item.requestType}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Button color="inherit" onClick={() => setDetailTarget(item)} size="small" sx={{ textTransform: "none" }}>
                        <Box sx={{ textAlign: "left" }}>
                          <Typography sx={{ fontWeight: 600 }} variant="body2">
                            {item.objectName}
                          </Typography>
                          <Typography color="text.secondary" variant="caption">
                            {item.objectType}
                          </Typography>
                          {typeof (item.changeSummary as { after?: { owner_user_id?: string } }).after
                            ?.owner_user_id === "string" ? (
                            <Typography color="text.secondary" sx={{ display: "block" }} variant="caption">
                              Yeni sahip:{" "}
                              {(item.changeSummary as { after: { owner_user_id: string } }).after.owner_user_id}
                            </Typography>
                          ) : null}
                        </Box>
                      </Button>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{item.scopeType}</Typography>
                      <Typography color="text.secondary" variant="caption">
                        {item.scopeId}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{item.makerActorId}</Typography>
                      {item.checkerActorId ? (
                        <Typography color="text.secondary" variant="caption">
                          Karar: {item.checkerActorId}
                        </Typography>
                      ) : null}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{formatDateTime(item.requestedAt)}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{formatDateTime(item.decidedAt)}</Typography>
                      {item.reasonCode ? (
                        <Typography color="text.secondary" variant="caption">
                          {item.reasonCode}
                        </Typography>
                      ) : null}
                    </TableCell>
                    <TableCell>
                      <Chip
                        color={statusColors[item.status] ?? "default"}
                        label={governanceStatusLabels[item.status] ?? item.status}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {governanceRemainingLabel(item, now) ?? "—"}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Stack direction="row" sx={{ gap: 1, justifyContent: "flex-end" }}>
                        {item.availableActions.includes("DECIDE_APPROVAL") && (
                          <Button
                            color="success"
                            onClick={() => {
                              setDecision("APPROVE");
                              setDecisionReason(governanceDecisionReasonCodes[0]);
                              setDecisionTarget(item);
                            }}
                            size="small"
                            variant="outlined"
                          >
                            {governanceActionLabels.DECIDE_APPROVAL}
                          </Button>
                        )}
                        {item.availableActions.includes("WITHDRAW_APPROVAL") && (
                          <Button
                            onClick={() => {
                              setWithdrawReason(governanceWithdrawReasonCodes[0]);
                              setWithdrawTarget(item);
                            }}
                            size="small"
                            variant="outlined"
                          >
                            {governanceActionLabels.WITHDRAW_APPROVAL}
                          </Button>
                        )}
                        {item.availableActions.includes("APPLY") && (
                          <Button
                            color="primary"
                            onClick={() => void onApply?.(item.approvalRequestId)}
                            size="small"
                            variant="contained"
                          >
                            {governanceActionLabels.APPLY}
                          </Button>
                        )}
                        {(item.domain === "QUALITY_RULE" ||
                          item.domain === "DATA_SOURCE" ||
                          item.domain === "METADATA_AND_CLASSIFICATION" ||
                          item.domain === "EXECUTION") && (
                          <Button component={Link} size="small" to={governanceTargetHref(item)}>
                            Hedefe git
                          </Button>
                        )}
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Box>

      <Dialog onClose={() => setDecisionTarget(null)} open={decisionTarget !== null}>
        <DialogTitle>Karar ver — {decisionTarget?.objectName}</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, minWidth: { sm: 420 }, pt: "16px !important" }}>
          <ToggleButtonGroup
            color="primary"
            exclusive
            onChange={(_event, next: "APPROVE" | "REJECT" | null) => {
              if (next) setDecision(next);
            }}
            size="small"
            value={decision}
          >
            <ToggleButton value="APPROVE">Onayla</ToggleButton>
            <ToggleButton value="REJECT">Reddet</ToggleButton>
          </ToggleButtonGroup>
          <TextField
            label="Gerekçe kodu"
            onChange={(event) => setDecisionReason(event.target.value)}
            select
            value={decisionReason}
          >
            {governanceDecisionReasonCodes.map((code) => (
              <MenuItem key={code} value={code}>
                {code}
              </MenuItem>
            ))}
          </TextField>
          <Typography color="text.secondary" variant="caption">
            Karar, maker-checker denetimiyle backend'de doğrulanır ve audit kaydı oluşturur.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDecisionTarget(null)}>Vazgeç</Button>
          <Button
            color={decision === "APPROVE" ? "success" : "error"}
            onClick={() => {
              if (decisionTarget) void onDecide?.(decisionTarget.approvalRequestId, decision, decisionReason);
              setDecisionTarget(null);
            }}
            variant="contained"
          >
            {decision === "APPROVE" ? "Onayla" : "Reddet"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog onClose={() => setWithdrawTarget(null)} open={withdrawTarget !== null}>
        <DialogTitle>Talebi geri çek — {withdrawTarget?.objectName}</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, minWidth: { sm: 420 }, pt: "16px !important" }}>
          <TextField
            label="Gerekçe kodu"
            onChange={(event) => setWithdrawReason(event.target.value)}
            select
            value={withdrawReason}
          >
            {governanceWithdrawReasonCodes.map((code) => (
              <MenuItem key={code} value={code}>
                {code}
              </MenuItem>
            ))}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setWithdrawTarget(null)}>Vazgeç</Button>
          <Button
            onClick={() => {
              if (withdrawTarget) void onWithdraw?.(withdrawTarget.approvalRequestId, withdrawReason);
              setWithdrawTarget(null);
            }}
            variant="contained"
          >
            Geri Çek
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog onClose={() => setDetailTarget(null)} open={detailTarget !== null}>
        <DialogTitle>Talep detayı</DialogTitle>
        <DialogContent sx={{ minWidth: { sm: 480 } }}>
          {detailTarget ? (
            <Stack sx={{ gap: 1.5 }}>
              <Typography variant="body2">
                <strong>Talep:</strong>{" "}
                {governanceRequestTypeLabels[detailTarget.requestType] ?? detailTarget.requestType}
              </Typography>
              <Typography variant="body2">
                <strong>Hedef:</strong> {detailTarget.objectName} ({detailTarget.objectType})
              </Typography>
              <Typography variant="body2">
                <strong>Kapsam:</strong> {detailTarget.scopeType} / {detailTarget.scopeId}
              </Typography>
              <Typography variant="body2">
                <strong>Maker:</strong> {detailTarget.makerActorId}
              </Typography>
              <Typography variant="body2">
                <strong>Checker:</strong> {detailTarget.checkerActorId ?? "—"}
              </Typography>
              <Typography variant="body2">
                <strong>Durum:</strong> {governanceStatusLabels[detailTarget.status] ?? detailTarget.status}
              </Typography>
              <Typography variant="body2">
                <strong>Politika:</strong> {detailTarget.policyVersion}
              </Typography>
              {Object.keys(detailTarget.changeSummary).length ? (
                <Box component="pre" sx={{ bgcolor: "action.hover", borderRadius: 1, fontSize: 12, overflow: "auto", p: 1.5 }}>
                  {JSON.stringify(detailTarget.changeSummary, null, 2)}
                </Box>
              ) : null}
            </Stack>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailTarget(null)}>Kapat</Button>
        </DialogActions>
      </Dialog>

      <Dialog onClose={() => setCreateOpen(false)} open={createOpen}>
        <DialogTitle>Yönetişim talebi oluştur</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, minWidth: { sm: 460 }, pt: "16px !important" }}>
          <TextField
            label="Talep alanı"
            onChange={(event) => handleKindChange(event.target.value as CreateRequestKind)}
            select
            value={createKind}
          >
            {(Object.keys(createKindLabels) as CreateRequestKind[]).map((kind) => (
              <MenuItem key={kind} value={kind}>
                {createKindLabels[kind]}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Dataset / Tablo"
            onChange={(event) => handleCreateDatasetChange(event.target.value)}
            select
            value={createDatasetId}
          >
            {datasets.map((dataset) => (
              <MenuItem key={dataset.id} value={dataset.id}>
                {dataset.namespace}.{dataset.name}
              </MenuItem>
            ))}
          </TextField>

          {createKind === "OWNERSHIP" ? (
            <>
              <TextField
                label="İşlem"
                disabled
                value={selectedDataset ? (selectedDataset.ownerId ? "Sahip değişikliği" : "Sahip atama") : ""}
              />
              <Autocomplete
                disabled={!createDatasetId}
                filterOptions={(options, state) =>
                  filterGovernanceOwnerCandidates(options, state.inputValue)
                }
                getOptionLabel={(option) => `${option.displayName} (${option.id})`}
                isOptionEqualToValue={(option, value) => option.id === value.id}
                noOptionsText="Eşleşen kullanıcı bulunamadı"
                onChange={(_event, option) => setCreateOwner(option?.id ?? "")}
                options={selectableOwnerCandidates}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    helperText="Kullanıcı adı, kimliği veya rolüne göre arayın; en fazla 5 sonuç gösterilir."
                    label="Yeni sahip"
                  />
                )}
                renderOption={(props, option) => (
                  <Box component="li" {...props} key={option.id}>
                    <Stack>
                      <Typography variant="body2">{option.displayName}</Typography>
                      <Typography color="text.secondary" variant="caption">
                        {option.id} · {option.roles}
                      </Typography>
                    </Stack>
                  </Box>
                )}
                value={selectableOwnerCandidates.find((candidate) => candidate.id === createOwner) ?? null}
              />
            </>
          ) : null}

          {createKind === "METADATA" ? (
            <>
              <TextField
                label="Kritik öznitelik"
                onChange={(event) => {
                  const attribute = event.target.value as "criticality" | "status";
                  setCreateMetaAttribute(attribute);
                  setCreateMetaValue(attribute === "criticality" ? "CRITICAL" : "INACTIVE");
                  setCreateReason(
                    attribute === "criticality"
                      ? governanceMetadataReasonCodes[0]
                      : governanceMetadataReasonCodes[1],
                  );
                }}
                select
                value={createMetaAttribute}
              >
                <MenuItem value="criticality">Kritiklik</MenuItem>
                <MenuItem value="status">Durum</MenuItem>
              </TextField>
              <TextField
                label="Yeni değer"
                onChange={(event) => setCreateMetaValue(event.target.value)}
                select
                value={createMetaValue}
              >
                {(createMetaAttribute === "criticality" ? criticalityOptions : datasetStatusOptions).map(
                  (value) => (
                    <MenuItem key={value} value={value}>
                      {value}
                    </MenuItem>
                  ),
                )}
              </TextField>
            </>
          ) : null}

          {createKind === "FIELD_SENSITIVITY" ? (
            <>
              <TextField
                label="Alan"
                disabled={!createDatasetId || createFieldsLoading}
                helperText={createFieldsLoading ? "Alanlar yükleniyor…" : undefined}
                onChange={(event) => setCreateFieldId(event.target.value)}
                select
                value={createFieldId}
              >
                {createFields.map((candidate) => (
                  <MenuItem key={candidate.id} value={candidate.id}>
                    {candidate.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                label="Hassasiyet"
                onChange={(event) => setCreateSensitive(event.target.value === "SENSITIVE")}
                select
                value={createSensitive ? "SENSITIVE" : "NOT_SENSITIVE"}
              >
                <MenuItem value="SENSITIVE">Hassas</MenuItem>
                <MenuItem value="NOT_SENSITIVE">Hassas değil</MenuItem>
              </TextField>
              <TextField
                label="Sınıflandırma"
                onChange={(event) => setCreateClassification(event.target.value)}
                select
                value={createClassification}
              >
                {CLASSIFICATION_OPTIONS.map((code) => (
                  <MenuItem key={code} value={code}>
                    {code}
                  </MenuItem>
                ))}
              </TextField>
            </>
          ) : null}

          <TextField
            label="Gerekçe kodu"
            onChange={(event) => setCreateReason(event.target.value)}
            select
            value={createReason}
          >
            {(createKind === "OWNERSHIP"
              ? governanceOwnershipReasonCodes
              : createKind === "METADATA"
                ? governanceMetadataReasonCodes
                : governanceFieldSensitivityReasonCodes
            ).map((code) => (
              <MenuItem key={code} value={code}>
                {code}
              </MenuItem>
            ))}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>Vazgeç</Button>
          <Button disabled={!createEnabled} onClick={handleSubmitCreate} variant="contained">
            Onaya Gönder
          </Button>
        </DialogActions>
      </Dialog>
    </AppShell>
  );
}
