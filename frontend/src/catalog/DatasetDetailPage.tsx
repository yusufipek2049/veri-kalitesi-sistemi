import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Paper,
  Skeleton,
  Typography,
} from "@mui/material";
import { ArrowLeft, RefreshCw, Search as SearchIcon } from "lucide-react";
import { Link } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import type {
  CatalogDataset,
  CatalogField,
  CatalogItemStatus,
  DatasetDetailState,
  DiscoveryStatus,
  MetadataDiff,
} from "./model";

interface DatasetDetailPageProps {
  state?: DatasetDetailState;
  dataset?: CatalogDataset;
  dataSourceName?: string;
  fields?: CatalogField[];
  discoveryStatus?: DiscoveryStatus | null;
  latestDiff?: MetadataDiff | null;
  correlationId?: string;
  onRefresh?: () => void;
  onRequestDiscovery?: (dataSourceId: string) => Promise<void>;
  onApplyDiff?: (metadataDiffId: string) => Promise<void>;
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

function FieldRow({ field }: { field: CatalogField }) {
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
          xs: "minmax(0, 1fr)",
          md: "minmax(180px, 1fr) 120px 80px 80px 120px",
        },
        minHeight: 56,
        px: 4,
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
        {field.nativeDataType}
      </Typography>
      <Typography color="text.secondary" variant="body2">
        {field.isNullable ? "Evet" : "Hayır"}
      </Typography>
      <Typography color="text.secondary" variant="body2">
        {field.isSensitive ? "Evet" : "Hayır"}
      </Typography>
      <StatusBadge label={field.status} tone={fieldStatusTone(field.status)} />
    </Box>
  );
}

export function DatasetDetailPage({
  state = "normal",
  dataset,
  dataSourceName,
  fields = [],
  discoveryStatus,
  latestDiff,
  correlationId,
  onRefresh,
  onRequestDiscovery,
  onApplyDiff,
}: DatasetDetailPageProps) {
  const [fieldQuery, setFieldQuery] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [discovering, setDiscovering] = useState(false);
  const [applying, setApplying] = useState(false);

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

  const handleApplyDiff = async () => {
    if (!latestDiff?.metadataDiffId || !onApplyDiff) return;
    setApplying(true);
    setActionError(null);
    try {
      await onApplyDiff(latestDiff.metadataDiffId);
    } catch {
      setActionError("Fark uygulaması tamamlanamadı.");
    } finally {
      setApplying(false);
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
              <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr 1fr 1fr" } }}>
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
                {discoveryStatus.partialReasonCode ? (
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
                  {onApplyDiff ? (
                    <Button
                      disabled={applying}
                      onClick={() => void handleApplyDiff()}
                      variant="contained"
                    >
                      Farkı uygula
                    </Button>
                  ) : null}
                </Box>
                <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                  <Chip color="success" label={`+${latestDiff.addedObjects.length} yeni`} size="small" variant="outlined" />
                  <Chip color="warning" label={`~${latestDiff.changedObjects.length} değişti`} size="small" variant="outlined" />
                  <Chip color="error" label={`-${latestDiff.removedObjects.length} kaldırıldı`} size="small" variant="outlined" />
                  {latestDiff.requiresRuleReview ? (
                    <Chip color="info" label="Kural incelemesi gerekli" size="small" />
                  ) : null}
                </Box>
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
          </>
        ) : null}
      </Box>
    </AppShell>
  );
}
