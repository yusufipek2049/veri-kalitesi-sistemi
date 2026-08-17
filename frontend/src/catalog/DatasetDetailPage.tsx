import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  FormGroup,
  MenuItem,
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
import { ArrowLeft, Edit, Eye, ListChecks, RefreshCw, Search as SearchIcon, ShieldAlert, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { timelinessNatureLabels } from "../jobs/model";
import { CatalogApiError } from "./api";
import { diffObjectSelection, type DiffObjectSelection } from "./model";
import type {
  CatalogDataset,
  CatalogField,
  CatalogItemStatus,
  DatasetDetailState,
  DatasetPreview,
  DatasetUpdatePayload,
  DiscoveryStatus,
  MetadataDiff,
} from "./model";

const diffObjectLabel = (object: Record<string, unknown>): string => {
  const namespace = String(object.namespace ?? "");
  const datasetName = String(object.dataset_name ?? "");
  const fieldName = object.field_name;
  const base = namespace ? `${namespace}.${datasetName}` : datasetName;
  return typeof fieldName === "string" && fieldName ? `${base}.${fieldName}` : base;
};

interface DatasetRule {
  id: string;
  code: string;
  name: string;
  dimension: string;
  status: string;
  criticality: string;
  ruleType: string;
}

interface DatasetDetailPageProps {
  state?: DatasetDetailState;
  dataset?: CatalogDataset;
  dataSourceName?: string;
  fields?: CatalogField[];
  rules?: DatasetRule[];
  discoveryStatus?: DiscoveryStatus | null;
  latestDiff?: MetadataDiff | null;
  correlationId?: string;
  onRefresh?: () => void;
  onRequestDiscovery?: (dataSourceId: string) => Promise<void>;
  onSubmitDiffApproval?: (
    metadataDiffId: string,
    selectedObjects: DiffObjectSelection[],
  ) => Promise<void>;
  onUpdateDataset?: (payload: DatasetUpdatePayload) => Promise<void>;
  onSubmitAttributeChange?: (
    attribute: string,
    value: string,
    reasonCode: string,
  ) => Promise<void>;
  onPreviewRows?: () => Promise<DatasetPreview>;
}

const fieldStatusTone = (status: CatalogItemStatus): "success" | "unknown" =>
  status === "ACTIVE" ? "success" : "unknown";

const discoveryStatusTone = (
  status: string,
): "success" | "warning" | "critical" | "info" | "unknown" => {
  switch (status) {
    case "SUCCESS":
      return "success";
    case "PARTIAL":
      return "warning";
    case "TECHNICAL_ERROR":
      return "critical";
    case "RUNNING":
    case "QUEUED":
      return "info";
    default:
      return "unknown";
  }
};

const discoveryStatusLabels: Record<string, string> = {
  QUEUED: "Sırada",
  RUNNING: "Çalışıyor",
  SUCCESS: "Başarılı",
  PARTIAL: "Kısmi",
  TECHNICAL_ERROR: "Teknik hata",
  CANCELLED: "İptal",
};

const fieldColumns = ["Alan", "Veri tipi", "Boş olabilir", "Hassas veri", "Durum"];

const fieldGridSx = {
  display: "grid",
  gap: 3,
  gridTemplateColumns: {
    xs: "minmax(0, 1fr)",
    md: "minmax(180px, 1fr) 120px 100px 100px 120px",
  },
  px: 4,
} as const;

const ruleColumns = ["Kural", "Boyut", "Durum", "Kritiklik"];

const ruleGridSx = {
  display: "grid",
  gap: 2,
  gridTemplateColumns: {
    xs: "minmax(0, 1fr)",
    md: "minmax(200px, 1fr) 140px 120px 120px",
  },
  px: 4,
} as const;

const previewErrorMessages: Record<string, string> = {
  PREVIEW_UNSUPPORTED_SOURCE_TYPE:
    "Satır önizleme yalnızca PostgreSQL veri kaynakları için desteklenir.",
  DATA_SOURCE_NOT_ACTIVE:
    "Veri kaynağı aktif olmadığı için satır önizlemesi yapılamaz.",
  DATASET_FIELDS_MISSING:
    "Bu dataset için katalog alanı tanımlı olmadığından önizleme yapılamaz.",
};

/** Dar ekranda sütun başlığı satırı gizlendiği için etiket değerin yanında gösterilir. */
function CellLabel({ children }: { children: string }) {
  return (
    <Box
      component="span"
      sx={{ display: { xs: "inline", md: "none" }, fontWeight: 600, mr: 1 }}
    >
      {children}:
    </Box>
  );
}

function FieldTableHeader() {
  return (
    <Box
      component="li"
      sx={{
        ...fieldGridSx,
        alignItems: "center",
        bgcolor: "action.hover",
        borderBottom: 1,
        borderColor: "divider",
        display: { xs: "none", md: "grid" },
        py: 1.5,
      }}
    >
      {fieldColumns.map((column) => (
        <Typography color="text.secondary" key={column} sx={{ fontWeight: 700 }} variant="caption">
          {column}
        </Typography>
      ))}
    </Box>
  );
}

function FieldRow({ field }: { field: CatalogField }) {
  return (
    <Box
      component="li"
      sx={{
        ...fieldGridSx,
        alignItems: "center",
        borderBottom: 1,
        borderColor: "divider",
        minHeight: 56,
        py: 2,
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Box sx={{ minWidth: 0 }}>
        <Typography
          component={Link}
          noWrap
          sx={{ fontWeight: 600, textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
          to={`/catalog/fields/${field.id}`}
          variant="body2"
        >
          {field.name}
        </Typography>
      </Box>
      <Typography color="text.secondary" variant="body2">
        <CellLabel>Veri tipi</CellLabel>
        {field.nativeDataType}
      </Typography>
      <Typography color="text.secondary" variant="body2">
        <CellLabel>Boş olabilir</CellLabel>
        {field.isNullable ? "Evet" : "Hayır"}
      </Typography>
      <Typography color="text.secondary" variant="body2">
        <CellLabel>Hassas veri</CellLabel>
        {field.isSensitive ? "Evet" : "Hayır"}
      </Typography>
      <Box sx={{ alignItems: "center", display: "flex" }}>
        <Typography color="text.secondary" variant="body2">
          <CellLabel>Durum</CellLabel>
        </Typography>
        <StatusBadge label={field.status} tone={fieldStatusTone(field.status)} />
      </Box>
    </Box>
  );
}

export function DatasetDetailPage({
  state = "normal",
  dataset,
  dataSourceName,
  fields = [],
  rules = [],
  discoveryStatus,
  latestDiff,
  correlationId,
  onRefresh,
  onRequestDiscovery,
  onSubmitDiffApproval,
  onUpdateDataset,
  onSubmitAttributeChange,
  onPreviewRows,
}: DatasetDetailPageProps) {
  const [fieldQuery, setFieldQuery] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [discovering, setDiscovering] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [selectedDiffKeys, setSelectedDiffKeys] = useState<ReadonlySet<string>>(new Set());
  const [diffSubmitted, setDiffSubmitted] = useState(false);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editForm, setEditForm] = useState({ name: "", namespace: "" });
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Governance attribute change dialog state
  const [attrDialogOpen, setAttrDialogOpen] = useState(false);
  const [attrAttribute, setAttrAttribute] = useState("criticality");
  const [attrValue, setAttrValue] = useState("CRITICAL");
  const [attrSaving, setAttrSaving] = useState(false);
  const [attrError, setAttrError] = useState<string | null>(null);
  const [attrSuccess, setAttrSuccess] = useState(false);

  const filteredFields = fields.filter((f) =>
    f.name.toLocaleLowerCase("tr-TR").includes(fieldQuery.toLocaleLowerCase("tr-TR")),
  );

  const handleDiscover = async () => {
    if (!dataset || !onRequestDiscovery) return;
    setDiscovering(true);
    setActionError(null);
    try {
      await onRequestDiscovery(dataset.dataSourceId);
    } catch {
      setActionError("Metadata keşif başlatılamadı.");
    } finally {
      setDiscovering(false);
    }
  };

  useEffect(() => {
    setSelectedDiffKeys(new Set());
    setDiffSubmitted(false);
  }, [latestDiff?.metadataDiffId]);

  const diffGroups = latestDiff
    ? ([
        { changeType: "ADDED", title: "Yeni", color: "success", objects: latestDiff.addedObjects },
        { changeType: "CHANGED", title: "Değişen", color: "warning", objects: latestDiff.changedObjects },
        { changeType: "REMOVED", title: "Kaldırılan", color: "error", objects: latestDiff.removedObjects },
      ] as const)
    : [];

  const toggleDiffObject = (key: DiffObjectSelection) => {
    const serialized = JSON.stringify(key);
    setSelectedDiffKeys((prev) => {
      const next = new Set(prev);
      if (next.has(serialized)) {
        next.delete(serialized);
      } else {
        next.add(serialized);
      }
      return next;
    });
  };

  const handleSubmitDiffApproval = async () => {
    if (!latestDiff?.metadataDiffId || !onSubmitDiffApproval || selectedDiffKeys.size === 0) return;
    setSubmitting(true);
    setActionError(null);
    try {
      const selectedObjects = [...selectedDiffKeys].map(
        (serialized) => JSON.parse(serialized) as DiffObjectSelection,
      );
      await onSubmitDiffApproval(latestDiff.metadataDiffId, selectedObjects);
      setDiffSubmitted(true);
    } catch {
      setActionError("Onay talebi gönderilemedi.");
    } finally {
      setSubmitting(false);
    }
  };

  const handlePreviewRows = async () => {
    if (!onPreviewRows) return;
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      setPreview(await onPreviewRows());
    } catch (error) {
      if (error instanceof CatalogApiError) {
        setPreviewError(
          previewErrorMessages[error.detail] ??
            `Satır önizlemesi yüklenemedi (${error.detail}).`,
        );
      } else {
        setPreviewError("Satır önizlemesi yüklenemedi.");
      }
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleOpenEdit = () => {
    if (!dataset) return;
    setEditForm({ name: dataset.name, namespace: dataset.namespace });
    setEditError(null);
    setEditDialogOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!dataset || !onUpdateDataset) return;
    setEditSaving(true);
    setEditError(null);
    try {
      const payload: DatasetUpdatePayload = { expected_version: dataset.version };
      if (editForm.name !== dataset.name) payload.name = editForm.name;
      if (editForm.namespace !== dataset.namespace) payload.namespace = editForm.namespace;
      await onUpdateDataset(payload);
      setEditDialogOpen(false);
    } catch {
      setEditError("Dataset güncellenemedi. Lütfen tekrar deneyin.");
    } finally {
      setEditSaving(false);
    }
  };

  // Governance attribute change helpers
  const attributeOptions: Record<string, { label: string; values: string[]; reason: string }> = {
    criticality: {
      label: "Kritiklik",
      values: ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
      reason: "METADATA.CRITICALITY.CHANGE",
    },
    status: {
      label: "Durum",
      values: ["ACTIVE", "INACTIVE"],
      reason: "METADATA.STATUS.CHANGE",
    },
    timeliness_nature: {
      label: "Zamanlılık niteliği",
      values: ["NEAR_TIME", "REAL_TIME", "BATCH_TIME"],
      reason: "METADATA.TIMELINESS.CHANGE",
    },
  };

  const currentAttributeValue =
    attrAttribute === "criticality"
      ? dataset?.criticality
      : attrAttribute === "status"
        ? dataset?.status
        : dataset?.timelinessNature ?? "—";

  const handleAttributeChange = (attribute: string) => {
    setAttrAttribute(attribute);
    const first = attributeOptions[attribute]?.values[0] ?? "";
    setAttrValue(first);
    setAttrError(null);
    setAttrSuccess(false);
  };

  const handleSubmitAttributeChange = async () => {
    if (!dataset || !onSubmitAttributeChange) return;
    setAttrSaving(true);
    setAttrError(null);
    setAttrSuccess(false);
    try {
      const reason = attributeOptions[attrAttribute]?.reason ?? "METADATA.CRITICALITY.CHANGE";
      await onSubmitAttributeChange(attrAttribute, attrValue, reason);
      setAttrSuccess(true);
    } catch {
      setAttrError("Nitelik değişiklik talebi gönderilemedi.");
    } finally {
      setAttrSaving(false);
    }
  };

  return (
    <AppShell currentPage="Katalog">
      <Box
        sx={(theme) => ({
          display: "grid",
          gap: 5,
          margin: "0 auto",
          maxWidth: theme.appLayout.contentMaxWidth,
          p: { xs: 3, md: 4, lg: 6 },
          width: "100%",
        })}
      >
        <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
          <Button
            component={Link}
            to="/catalog"
            startIcon={<ArrowLeft aria-hidden="true" size={16} />}
            variant="text"
          >
            Katalog
          </Button>
        </Box>

        {state === "loading" ? (
          <Box aria-busy="true">
            <Skeleton height={40} />
            <Skeleton height={200} sx={{ mt: 2 }} />
            <Skeleton height={300} sx={{ mt: 2 }} />
          </Box>
        ) : null}

        {state === "error" ? (
          <Alert severity="error">
            <Typography sx={{ fontWeight: 700 }}>Dataset yüklenemedi</Typography>
            <Typography variant="body2">
              İzleme kodu: {correlationId ?? "bulunamadı"}.
            </Typography>
          </Alert>
        ) : null}

        {state === "unauthorized" ? (
          <Alert severity="warning">
            <Typography sx={{ fontWeight: 700 }}>Bu görünüm için yetkiniz yok</Typography>
            <Typography variant="body2">Dataset içeriği gösterilmedi.</Typography>
          </Alert>
        ) : null}

        {state === "not-found" ? (
          <Alert severity="info">
            <Typography sx={{ fontWeight: 700 }}>Dataset bulunamadı</Typography>
            <Typography variant="body2">İstenen katalog kaydı mevcut değil.</Typography>
          </Alert>
        ) : null}

        {state === "normal" && dataset ? (
          <>
            <Box
              sx={{
                alignItems: { md: "center" },
                display: "flex",
                flexDirection: { xs: "column", md: "row" },
                gap: 3,
                justifyContent: "space-between",
              }}
            >
              <Box>
                <Typography component="h1" variant="h1">
                  {dataset.name}
                </Typography>
                <Typography color="text.secondary">
                  {dataSourceName ?? dataset.dataSourceId} · {dataset.namespace}
                </Typography>
              </Box>
              <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                <Button
                  component={Link}
                  to={`/catalog/datasets/${dataset.id}/trend`}
                  startIcon={<TrendingUp aria-hidden="true" size={16} />}
                  variant="contained"
                >
                  Skor trendi
                </Button>
                {onRequestDiscovery ? (
                  <Button
                    disabled={discovering}
                    onClick={() => void handleDiscover()}
                    startIcon={<RefreshCw aria-hidden="true" size={16} />}
                    variant="contained"
                  >
                    Metadata keşfet
                  </Button>
                ) : null}
                {onUpdateDataset ? (
                  <Button
                    onClick={handleOpenEdit}
                    startIcon={<Edit aria-hidden="true" size={16} />}
                    variant="outlined"
                  >
                    Düzenle
                  </Button>
                ) : null}
                {onSubmitAttributeChange ? (
                  <Button
                    onClick={() => {
                      setAttrError(null);
                      setAttrSuccess(false);
                      setAttrDialogOpen(true);
                    }}
                    startIcon={<ShieldAlert aria-hidden="true" size={16} />}
                    variant="outlined"
                  >
                    Nitelik Değiştir
                  </Button>
                ) : null}
                <Button onClick={onRefresh} variant="outlined">
                  Yenile
                </Button>
              </Box>
            </Box>

            {actionError ? (
              <Alert onClose={() => setActionError(null)} severity="error">
                {actionError}
              </Alert>
            ) : null}

            {/* Dataset metadata summary */}
            <Paper variant="outlined" sx={{ borderRadius: 1.5, p: 4 }}>
              <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr 1fr 1fr 1fr 1fr" } }}>
                <Box>
                  <Typography color="text.secondary" variant="caption">
                    Tip
                  </Typography>
                  <Typography sx={{ fontWeight: 600 }}>{dataset.datasetType}</Typography>
                </Box>
                <Box>
                  <Typography color="text.secondary" variant="caption">
                    Durum
                  </Typography>
                  <StatusBadge
                    label={dataset.status}
                    tone={dataset.status === "ACTIVE" ? "success" : "unknown"}
                  />
                </Box>
                <Box>
                  <Typography color="text.secondary" variant="caption">
                    Kritiklik
                  </Typography>
                  <Chip
                    color={
                      dataset.criticality === "CRITICAL"
                        ? "error"
                        : dataset.criticality === "HIGH"
                          ? "warning"
                          : dataset.criticality === "MEDIUM"
                            ? "info"
                            : "default"
                    }
                    label={dataset.criticality}
                    size="small"
                    sx={{ mt: 0.5 }}
                  />
                </Box>
                <Box>
                  <Typography color="text.secondary" variant="caption">
                    Alan sayısı
                  </Typography>
                  <Typography sx={{ fontWeight: 600 }}>{dataset.fieldCount}</Typography>
                </Box>
                <Box>
                  <Typography color="text.secondary" variant="caption">
                    Tahmini satır
                  </Typography>
                  <Typography sx={{ fontWeight: 600 }}>
                    {dataset.estimatedRowCount?.toLocaleString("tr-TR") ?? "—"}
                  </Typography>
                </Box>
                <Box>
                  <Typography color="text.secondary" variant="caption">
                    Zamanlılık niteliği
                  </Typography>
                  {dataset.timelinessNature ? (
                    <Chip
                      color={
                        dataset.timelinessNature === "REAL_TIME"
                          ? "success"
                          : dataset.timelinessNature === "NEAR_TIME"
                            ? "info"
                            : "warning"
                      }
                      label={timelinessNatureLabels[dataset.timelinessNature]}
                      size="small"
                      sx={{ mt: 0.5 }}
                    />
                  ) : (
                    <Typography color="text.secondary" sx={{ fontWeight: 600 }}>
                      Atanmadı (job için gerekli)
                    </Typography>
                  )}
                </Box>
              </Box>
            </Paper>

            {/* Discovery status panel */}
            {discoveryStatus ? (
              <Paper variant="outlined" sx={{ borderRadius: 1.5, p: 4 }}>
                <Typography component="h2" sx={{ fontWeight: 700, mb: 2 }} variant="h3">
                  Son Keşif
                </Typography>
                <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr 1fr" } }}>
                  <Box>
                    <Typography color="text.secondary" variant="caption">
                      Durum
                    </Typography>
                    <Box sx={{ mt: 0.5 }}>
                      <StatusBadge
                        label={discoveryStatusLabels[discoveryStatus.status] ?? discoveryStatus.status}
                        tone={discoveryStatusTone(discoveryStatus.status)}
                      />
                    </Box>
                  </Box>
                  <Box>
                    <Typography color="text.secondary" variant="caption">
                      Taranan nesne
                    </Typography>
                    <Typography sx={{ fontWeight: 600 }}>
                      {discoveryStatus.scannedObjectCount}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography color="text.secondary" variant="caption">
                      Bitiş
                    </Typography>
                    <Typography sx={{ fontWeight: 600 }}>
                      {discoveryStatus.finishedAt
                        ? new Date(discoveryStatus.finishedAt).toLocaleString("tr-TR")
                        : "—"}
                    </Typography>
                  </Box>
                </Box>
                {(discoveryStatus.status === "RUNNING" || discoveryStatus.status === "QUEUED") ? (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    <Box sx={{ alignItems: "center", display: "flex", gap: 1 }}>
                      <CircularProgress aria-label="Keşif devam ediyor" size={16} />
                      <Typography variant="body2">Metadata keşfi işlemi devam ediyor...</Typography>
                    </Box>
                  </Alert>
                ) : null}
                {discoveryStatus.status === "TECHNICAL_ERROR" ? (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    <Typography variant="body2">
                      Keşif sırasında teknik hata oluştu.
                      {discoveryStatus.partialReasonCode ? ` (${discoveryStatus.partialReasonCode})` : ""}
                    </Typography>
                  </Alert>
                ) : null}
                {discoveryStatus.partialReasonCode && discoveryStatus.status !== "TECHNICAL_ERROR" ? (
                  <Alert severity="warning" sx={{ mt: 2 }}>
                    Kısmi sonuç: {discoveryStatus.partialReasonCode}
                  </Alert>
                ) : null}
              </Paper>
            ) : null}

            {/* Metadata diff panel */}
            {latestDiff && latestDiff.status === "PENDING" ? (
              <Paper variant="outlined" sx={{ borderRadius: 1.5, p: 4 }}>
                <Box sx={{ alignItems: "center", display: "flex", justifyContent: "space-between", mb: 2 }}>
                  <Typography component="h2" sx={{ fontWeight: 700 }} variant="h3">
                    Bekleyen Fark
                  </Typography>
                  {onSubmitDiffApproval && !diffSubmitted ? (
                    <Button
                      disabled={submitting || selectedDiffKeys.size === 0}
                      onClick={() => void handleSubmitDiffApproval()}
                      variant="contained"
                    >
                      Onaya gönder
                    </Button>
                  ) : null}
                </Box>
                {diffSubmitted ? (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Onay bekleniyor. Seçilen değişiklikler onay süreci tamamlanınca uygulanacak.
                  </Alert>
                ) : null}
                {latestDiff.requiresRuleReview ? (
                  <Chip color="info" label="Kural incelemesi gerekli" size="small" sx={{ mb: 1 }} />
                ) : null}
                {diffGroups.map((group) =>
                  group.objects.length === 0 ? null : (
                    <Box key={group.changeType} sx={{ mt: 2 }}>
                      <Chip
                        color={group.color}
                        label={`${group.title} (${group.objects.length})`}
                        size="small"
                        variant="outlined"
                      />
                      <FormGroup sx={{ mt: 1 }}>
                        {group.objects.map((object) => {
                          const key = diffObjectSelection(group.changeType, object);
                          const serialized = JSON.stringify(key);
                          return (
                            <FormControlLabel
                              key={serialized}
                              control={
                                <Checkbox
                                  checked={selectedDiffKeys.has(serialized)}
                                  disabled={diffSubmitted || !onSubmitDiffApproval}
                                  onChange={() => toggleDiffObject(key)}
                                  size="small"
                                />
                              }
                              label={diffObjectLabel(object)}
                            />
                          );
                        })}
                      </FormGroup>
                    </Box>
                  ),
                )}
              </Paper>
            ) : null}

            {/* Fields table */}
            <Paper variant="outlined" sx={{ borderRadius: 1.5, overflow: "hidden" }}>
              <Box
                sx={{
                  alignItems: "center",
                  borderBottom: 1,
                  borderColor: "divider",
                  display: "flex",
                  justifyContent: "space-between",
                  px: 4,
                  py: 3,
                }}
              >
                <Typography component="h2" variant="h3">
                  Alanlar
                </Typography>
                <Typography color="text.secondary" variant="body2">
                  {filteredFields.length} alan
                </Typography>
              </Box>
              <Box sx={{ px: 4, py: 2 }}>
                <Box sx={{ alignItems: "center", display: "flex", gap: 1 }}>
                  <SearchIcon aria-hidden="true" size={16} />
                  <input
                    aria-label="Alan ara"
                    onChange={(e) => setFieldQuery(e.target.value)}
                    placeholder="Alan adı ara..."
                    style={{
                      border: "none",
                      outline: "none",
                      flex: 1,
                      fontSize: 14,
                      background: "transparent",
                      color: "inherit",
                    }}
                    value={fieldQuery}
                  />
                </Box>
              </Box>
              {filteredFields.length > 0 ? (
                <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
                  <FieldTableHeader />
                  {filteredFields.map((field) => (
                    <FieldRow field={field} key={field.id} />
                  ))}
                </Box>
              ) : (
                <Box sx={{ p: 4 }}>
                  <Alert severity="info">
                    <Typography variant="body2">Gösterilecek alan bulunamadı.</Typography>
                  </Alert>
                </Box>
              )}
            </Paper>

            {/* Data preview section */}
            {onPreviewRows ? (
              <Paper variant="outlined" sx={{ borderRadius: 1.5, overflow: "hidden" }}>
                <Box
                  sx={{
                    alignItems: "center",
                    borderBottom: 1,
                    borderColor: "divider",
                    display: "flex",
                    justifyContent: "space-between",
                    px: 4,
                    py: 3,
                  }}
                >
                  <Box sx={{ alignItems: "center", display: "flex", gap: 1 }}>
                    <Eye aria-hidden="true" size={20} />
                    <Typography component="h2" variant="h3">
                      Veri Önizleme
                    </Typography>
                  </Box>
                  <Button
                    disabled={previewLoading}
                    onClick={() => void handlePreviewRows()}
                    size="small"
                    startIcon={
                      previewLoading ? undefined : <RefreshCw aria-hidden="true" size={14} />
                    }
                    variant="contained"
                  >
                    {previewLoading ? "Yükleniyor..." : preview ? "Yeniden yükle" : "Satırları görüntüle"}
                  </Button>
                </Box>
                <Box sx={{ p: 4 }}>
                  {previewError ? (
                    <Alert onClose={() => setPreviewError(null)} severity="warning">
                      {previewError}
                    </Alert>
                  ) : null}
                  {!preview && !previewError ? (
                    <Typography color="text.secondary" variant="body2">
                      Kaynak tablodaki ilk satırları görüntülemek için "Satırları görüntüle"
                      düğmesini kullanın. Sorgu salt okunurdur ve en fazla 50 satır getirilir.
                    </Typography>
                  ) : null}
                  {previewLoading ? (
                    <Box sx={{ alignItems: "center", display: "flex", gap: 1, mt: preview ? 2 : 0 }}>
                      <CircularProgress aria-label="Satırlar yükleniyor" size={16} />
                      <Typography color="text.secondary" variant="body2">
                        Tablo satırları yükleniyor...
                      </Typography>
                    </Box>
                  ) : null}
                  {preview ? (
                    <Box sx={{ mt: previewError || previewLoading ? 2 : 0 }}>
                      <Box sx={{ alignItems: "center", display: "flex", flexWrap: "wrap", gap: 1, mb: 2 }}>
                        <Chip
                          label={`${preview.namespace}.${preview.tableName}`}
                          size="small"
                          variant="outlined"
                        />
                        <Typography color="text.secondary" variant="body2">
                          {preview.rows.length} satır (ilk {preview.limit} ile sınırlı)
                        </Typography>
                        {preview.columns.some((column) => column.isSensitive) ? (
                          <Chip color="warning" label="Hassas alanlar maskelendi" size="small" />
                        ) : null}
                      </Box>
                      {preview.rows.length === 0 ? (
                        <Alert severity="info">Tabloda gösterilecek satır bulunamadı.</Alert>
                      ) : (
                        <TableContainer sx={{ maxHeight: 480 }}>
                          <Table size="small" stickyHeader aria-label="Tablo satır önizlemesi">
                            <TableHead>
                              <TableRow>
                                {preview.columns.map((column) => (
                                  <TableCell key={column.name} sx={{ whiteSpace: "nowrap" }}>
                                    <Box sx={{ alignItems: "center", display: "flex", gap: 0.5 }}>
                                      <Typography sx={{ fontWeight: 700 }} variant="body2">
                                        {column.name}
                                      </Typography>
                                      {column.isSensitive ? (
                                        <Chip color="warning" label="Hassas" size="small" />
                                      ) : null}
                                    </Box>
                                    <Typography color="text.secondary" variant="caption">
                                      {column.nativeDataType}
                                    </Typography>
                                  </TableCell>
                                ))}
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {preview.rows.map((row, rowIndex) => (
                                <TableRow key={rowIndex}>
                                  {row.map((value, columnIndex) => (
                                    <TableCell
                                      key={preview.columns[columnIndex]?.name ?? columnIndex}
                                      sx={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                                    >
                                      {value === null ? (
                                        <Typography color="text.disabled" variant="body2">
                                          NULL
                                        </Typography>
                                      ) : (
                                        value
                                      )}
                                    </TableCell>
                                  ))}
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      )}
                    </Box>
                  ) : null}
                </Box>
              </Paper>
            ) : null}

            {/* Rules section */}
            <Paper variant="outlined" sx={{ borderRadius: 1.5, overflow: "hidden" }}>
              <Box
                sx={{
                  alignItems: "center",
                  borderBottom: 1,
                  borderColor: "divider",
                  display: "flex",
                  justifyContent: "space-between",
                  px: 4,
                  py: 3,
                }}
              >
                <Box sx={{ alignItems: "center", display: "flex", gap: 1 }}>
                  <ListChecks aria-hidden="true" size={20} />
                  <Typography component="h2" variant="h3">
                    Kalite Kuralları
                  </Typography>
                </Box>
                <Box sx={{ alignItems: "center", display: "flex", gap: 2 }}>
                  <Typography color="text.secondary" variant="body2">
                    {rules.length} kural
                  </Typography>
                  <Button component={Link} to="/rules" size="small" variant="text">
                    Tüm kurallar
                  </Button>
                </Box>
              </Box>
              {rules.length > 0 ? (
                <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
                  <Box
                    component="li"
                    sx={{
                      ...ruleGridSx,
                      alignItems: "center",
                      bgcolor: "action.hover",
                      borderBottom: 1,
                      borderColor: "divider",
                      display: { xs: "none", md: "grid" },
                      py: 1.5,
                    }}
                  >
                    {ruleColumns.map((column) => (
                      <Typography
                        color="text.secondary"
                        key={column}
                        sx={{ fontWeight: 700 }}
                        variant="caption"
                      >
                        {column}
                      </Typography>
                    ))}
                  </Box>
                  {rules.map((rule) => (
                    <Box
                      component="li"
                      key={rule.id}
                      sx={{
                        ...ruleGridSx,
                        alignItems: "center",
                        borderBottom: 1,
                        borderColor: "divider",
                        minHeight: 52,
                        py: 1.5,
                        "&:last-child": { borderBottom: 0 },
                      }}
                    >
                      <Box sx={{ minWidth: 0 }}>
                        <Typography
                          component={Link}
                          noWrap
                          sx={{ fontWeight: 600, textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
                          to="/rules"
                          variant="body2"
                        >
                          {rule.name}
                        </Typography>
                        <Typography color="text.secondary" noWrap variant="caption">
                          {rule.code}
                        </Typography>
                      </Box>
                      <Typography color="text.secondary" variant="body2">
                        <CellLabel>Boyut</CellLabel>
                        {rule.dimension}
                      </Typography>
                      <Box sx={{ alignItems: "center", display: "flex" }}>
                        <Typography color="text.secondary" variant="body2">
                          <CellLabel>Durum</CellLabel>
                        </Typography>
                        <StatusBadge
                          label={rule.status}
                          tone={rule.status === "ACTIVE" ? "success" : rule.status === "PASSIVE" ? "unknown" : "warning"}
                        />
                      </Box>
                      <Box sx={{ alignItems: "center", display: "flex" }}>
                        <Typography color="text.secondary" variant="body2">
                          <CellLabel>Kritiklik</CellLabel>
                        </Typography>
                        <Chip
                          label={rule.criticality}
                          size="small"
                          color={rule.criticality === "CRITICAL" ? "error" : rule.criticality === "HIGH" ? "warning" : "default"}
                          variant="outlined"
                        />
                      </Box>
                    </Box>
                  ))}
                </Box>
              ) : (
                <Box sx={{ p: 4 }}>
                  <Alert severity="info">
                    <Typography variant="body2">
                      Bu dataset için henüz kural tanımlanmamış.{" "}
                      <Link to="/rules" style={{ textDecoration: "underline" }}>
                        Kural oluştur
                      </Link>
                    </Typography>
                  </Alert>
                </Box>
              )}
            </Paper>
          </>
        ) : null}

        {/* Dataset edit dialog */}
        <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle>Dataset Düzenle</DialogTitle>
          <DialogContent>
            {editError ? (
              <Alert onClose={() => setEditError(null)} severity="error" sx={{ mb: 2 }}>
                {editError}
              </Alert>
            ) : null}
            <Box sx={{ display: "grid", gap: 2.5, mt: 1 }}>
              <TextField
                label="Ad"
                value={editForm.name}
                onChange={(e) => setEditForm((prev) => ({ ...prev, name: e.target.value }))}
                fullWidth
                required
                error={!editForm.name.trim()}
              />
              <TextField
                label="Namespace"
                value={editForm.namespace}
                onChange={(e) => setEditForm((prev) => ({ ...prev, namespace: e.target.value }))}
                fullWidth
                required
                error={!editForm.namespace.trim()}
              />
              <Alert severity="info">
                Durum, kritiklik ve zamanlılık niteliği değişiklikleri için "Nitelik
                Değiştir" butonunu kullanın.
              </Alert>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEditDialogOpen(false)} disabled={editSaving}>
              İptal
            </Button>
            <Button
              onClick={() => void handleSaveEdit()}
              disabled={editSaving || !editForm.name.trim() || !editForm.namespace.trim()}
              variant="contained"
            >
              {editSaving ? "Kaydediliyor..." : "Kaydet"}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Governance attribute change dialog */}
        <Dialog open={attrDialogOpen} onClose={() => setAttrDialogOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle>Kritik Nitelik Değişikliği</DialogTitle>
          <DialogContent>
            {attrError ? (
              <Alert onClose={() => setAttrError(null)} severity="error" sx={{ mb: 2 }}>
                {attrError}
              </Alert>
            ) : null}
            {attrSuccess ? (
              <Alert severity="success" sx={{ mb: 2 }}>
                Değişiklik talebi gönderildi. Onay sonrası uygulanacaktır.
              </Alert>
            ) : null}
            <Box sx={{ display: "grid", gap: 2.5, mt: 1 }}>
              <Alert severity="info">
                Bu nitelikler yönetişim onayı gerektirir. Talep gönderildikten sonra
                onaylanıp uygulanması gerekir.
              </Alert>
              <TextField
                label="Öznitelik"
                onChange={(e) => handleAttributeChange(e.target.value)}
                select
                value={attrAttribute}
              >
                {Object.entries(attributeOptions).map(([key, option]) => (
                  <MenuItem key={key} value={key}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
              <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
                <Typography color="text.secondary" variant="body2">
                  Mevcut değer:
                </Typography>
                <Typography sx={{ fontWeight: 600 }} variant="body2">
                  {currentAttributeValue}
                </Typography>
              </Box>
              <TextField
                label="Yeni değer"
                onChange={(e) => {
                  setAttrValue(e.target.value);
                  setAttrSuccess(false);
                }}
                select
                value={attrValue}
              >
                {(attributeOptions[attrAttribute]?.values ?? []).map((value) => (
                  <MenuItem key={value} value={value}>
                    {value}
                  </MenuItem>
                ))}
              </TextField>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setAttrDialogOpen(false)} disabled={attrSaving}>
              Kapat
            </Button>
            <Button
              onClick={() => void handleSubmitAttributeChange()}
              disabled={attrSaving || attrSuccess}
              variant="contained"
            >
              {attrSaving ? "Gönderiliyor..." : "Talep Gönder"}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </AppShell>
  );
}
