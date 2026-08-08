import {
  Alert,
  Box,
  Button,
  Chip,
  Paper,
  Skeleton,
  Typography,
} from "@mui/material";
import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import type { CatalogField, CatalogItemStatus, FieldDetailState } from "./model";

interface FieldDetailPageProps {
  state?: FieldDetailState;
  field?: CatalogField;
  datasetName?: string;
  dataSourceName?: string;
  correlationId?: string;
  onRefresh?: () => void;
}

const statusTone = (status: CatalogItemStatus): "success" | "unknown" =>
  status === "ACTIVE" ? "success" : "unknown";

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
      <Typography color="text.secondary" variant="caption">
        {label}
      </Typography>
      {children}
    </Box>
  );
}

export function FieldDetailPage({
  state = "normal",
  field,
  datasetName,
  dataSourceName,
  correlationId,
  onRefresh,
}: FieldDetailPageProps) {
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
            to={field ? `/catalog/datasets/${field.datasetId}` : "/catalog"}
            startIcon={<ArrowLeft aria-hidden="true" size={16} />}
            variant="text"
          >
            {datasetName ? datasetName : "Katalog"}
          </Button>
        </Box>

        {state === "loading" ? (
          <Box aria-busy="true">
            <Skeleton height={40} />
            <Skeleton height={200} sx={{ mt: 2 }} />
          </Box>
        ) : null}

        {state === "error" ? (
          <Alert severity="error">
            <Typography sx={{ fontWeight: 700 }}>Alan yüklenemedi</Typography>
            <Typography variant="body2">
              İzleme kodu: {correlationId ?? "bulunamadı"}.
            </Typography>
          </Alert>
        ) : null}

        {state === "unauthorized" ? (
          <Alert severity="warning">
            <Typography sx={{ fontWeight: 700 }}>Bu görünüm için yetkiniz yok</Typography>
            <Typography variant="body2">Alan içeriği gösterilmedi.</Typography>
          </Alert>
        ) : null}

        {state === "not-found" ? (
          <Alert severity="info">
            <Typography sx={{ fontWeight: 700 }}>Alan bulunamadı</Typography>
            <Typography variant="body2">İstenen katalog alanı mevcut değil.</Typography>
          </Alert>
        ) : null}

        {state === "normal" && field ? (
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
                  {field.name}
                </Typography>
                <Typography color="text.secondary">
                  {dataSourceName ? `${dataSourceName} · ` : ""}
                  {datasetName ?? field.datasetId}
                </Typography>
              </Box>
              <Button onClick={onRefresh} variant="outlined">
                Yenile
              </Button>
            </Box>

            <Paper variant="outlined" sx={{ borderRadius: 1.5, p: 4 }}>
              <Typography component="h2" sx={{ fontWeight: 700, mb: 3 }} variant="h3">
                Alan Özellikleri
              </Typography>
              <Box
                sx={{
                  display: "grid",
                  gap: 3,
                  gridTemplateColumns: { xs: "1fr", md: "1fr 1fr 1fr" },
                }}
              >
                <DetailRow label="Alan adı">
                  <Typography sx={{ fontWeight: 600 }}>{field.name}</Typography>
                </DetailRow>
                <DetailRow label="Yerel veri tipi">
                  <Typography sx={{ fontWeight: 600 }}>{field.nativeDataType}</Typography>
                </DetailRow>
                <DetailRow label="Durum">
                  <StatusBadge label={field.status} tone={statusTone(field.status)} />
                </DetailRow>
                <DetailRow label="Null olabilir">
                  <Typography sx={{ fontWeight: 600 }}>
                    {field.isNullable ? "Evet" : "Hayır"}
                  </Typography>
                </DetailRow>
                <DetailRow label="Hassas">
                  <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                    <Typography sx={{ fontWeight: 600 }}>
                      {field.isSensitive ? "Evet" : "Hayır"}
                    </Typography>
                    {field.isSensitive ? (
                      <Chip color="warning" label="Hassas veri" size="small" />
                    ) : null}
                  </Box>
                </DetailRow>
                <DetailRow label="Sınıflandırma">
                  <Typography sx={{ fontWeight: 600 }}>{field.classification}</Typography>
                </DetailRow>
              </Box>
            </Paper>

            <Paper variant="outlined" sx={{ borderRadius: 1.5, p: 4 }}>
              <Typography component="h2" sx={{ fontWeight: 700, mb: 2 }} variant="h3">
                Metadata
              </Typography>
              <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
                <DetailRow label="Alan kimliği">
                  <Typography sx={{ fontFamily: "monospace", fontWeight: 500 }} variant="body2">
                    {field.id}
                  </Typography>
                </DetailRow>
                <DetailRow label="Sürüm">
                  <Typography sx={{ fontWeight: 600 }}>v{field.version}</Typography>
                </DetailRow>
              </Box>
            </Paper>
          </>
        ) : null}
      </Box>
    </AppShell>
  );
}
