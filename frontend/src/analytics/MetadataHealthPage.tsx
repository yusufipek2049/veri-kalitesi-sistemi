import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Alert,
  Box,
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
  Tooltip,
  Typography,
} from "@mui/material";
import { Link } from "react-router-dom";
import { AnalyticsShell } from "./AnalyticsShell";
import { AnalyticsApiError, fetchMetadataHealth, type AnalyticsEnvelope } from "./api";
import {
  formatRatio,
  metadataHealthSummaryFromApi,
  ratioTooltip,
  type AnalyticsPageState,
  type MetadataHealthSummary,
} from "./model";

function KpiCard({ title, value, tooltip }: { title: string; value: string; tooltip?: string }) {
  return (
    <Card sx={{ minWidth: 180, flex: 1 }}>
      <CardContent>
        <Typography variant="caption" color="text.secondary">{title}</Typography>
        <Tooltip title={tooltip ?? ""}>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>{value}</Typography>
        </Tooltip>
      </CardContent>
    </Card>
  );
}

export function MetadataHealthPage() {
  const [searchParams] = useSearchParams();
  const [state, setState] = useState<AnalyticsPageState>("loading");
  const [data, setData] = useState<AnalyticsEnvelope | null>(null);
  const [summary, setSummary] = useState<MetadataHealthSummary | null>(null);
  const [correlationId, setCorrelationId] = useState<string>();

  const load = useCallback(async (signal?: AbortSignal) => {
    setState("loading");
    try {
      const response = await fetchMetadataHealth(
        {
          startDate: searchParams.get("start_date") ?? undefined,
          endDate: searchParams.get("end_date") ?? undefined,
          sourceId: searchParams.get("source_id") ?? undefined,
          datasetId: searchParams.get("dataset_id") ?? undefined,
        },
        undefined,
        signal,
      );
      if (signal?.aborted) return;
      setData(response);
      setCorrelationId(response.correlation_id);
      setSummary(metadataHealthSummaryFromApi(response.summary));
      setState(response.items.length > 0 ? "normal" : "empty");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof AnalyticsApiError) {
        setCorrelationId(error.correlationId);
        setState(error.kind === "forbidden" || error.kind === "unauthorized" ? "unauthorized" : "error");
      } else setState("error");
    }
  }, [searchParams]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  return (
    <AnalyticsShell activeTab="metadata-health" state={state} correlationId={correlationId}>
      {state === "loading" && (
        <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
          <CircularProgress aria-label="Yukleniyor" />
        </Box>
      )}
      {state === "error" && (
        <Alert severity="error">
          <Typography>Metadata sagligi verisi yuklenemedi.</Typography>
        </Alert>
      )}
      {state === "empty" && (
        <Alert severity="info">
          <Typography>Metadata acigi bulunamadi.</Typography>
        </Alert>
      )}
      {state === "normal" && summary && (
        <Stack spacing={3}>
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", gap: 1 }}>
            <KpiCard
              title="Sahiplik Tamligi"
              value={formatRatio(summary.ownershipCompleteness)}
              tooltip={ratioTooltip(summary.ownershipCompleteness)}
            />
            <KpiCard
              title="Siniflandirma Tamligi"
              value={formatRatio(summary.classificationCompleteness)}
              tooltip={ratioTooltip(summary.classificationCompleteness)}
            />
            <KpiCard
              title="Hassas Isaretleme"
              value={formatRatio(summary.sensitiveMarkingCompleteness)}
              tooltip={ratioTooltip(summary.sensitiveMarkingCompleteness)}
            />
            <KpiCard
              title="Politika Guncelligi"
              value={formatRatio(summary.policyCurrency)}
              tooltip={ratioTooltip(summary.policyCurrency)}
            />
            <KpiCard title="Eski Dataset" value={String(summary.staleDatasetCount)} />
            <KpiCard title="Kritik Acik" value={String(summary.criticalGapCount)} />
          </Stack>

          {/* Classification breakdown */}
          {data?.breakdowns?.by_classification ? (
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 1, fontWeight: 700 }}>
                  Siniflandirma Dagilimi
                </Typography>
                <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 0.5 }}>
                  {Object.entries(data.breakdowns.by_classification as Record<string, number>).map(
                    ([code, count]) => (
                      <Chip key={code} label={`${code}: ${count as number}`} size="small" variant="outlined" />
                    ),
                  )}
                </Stack>
              </CardContent>
            </Card>
          ) : null}

          {/* Critical gaps table */}
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
                Kritik Aciklar
              </Typography>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small" aria-label="Kritik metadata aciklari tablosu">
                  <TableHead>
                    <TableRow>
                      <TableCell>Tip</TableCell>
                      <TableCell>Ad</TableCell>
                      <TableCell>Kritiklik</TableCell>
                      <TableCell>Siniflandirma</TableCell>
                      <TableCell>Acik Kodu</TableCell>
                      <TableCell>Islem</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data?.items.slice(0, 50).map((item, idx) => (
                      <TableRow key={idx}>
                        <TableCell>{String(item.object_type ?? "")}</TableCell>
                        <TableCell>
                          {item.object_type === "dataset" ? (
                            <Link to={`/catalog/datasets/${String(item.object_id)}`}>
                              {String(item.display_name ?? item.object_id)}
                            </Link>
                          ) : item.object_type === "field" && item.dataset_id ? (
                            <Link to={`/catalog/fields/${String(item.object_id)}`}>
                              {String(item.display_name ?? item.object_id)}
                            </Link>
                          ) : (
                            String(item.display_name ?? "")
                          )}
                        </TableCell>
                        <TableCell>{String(item.criticality ?? "—")}</TableCell>
                        <TableCell>{String(item.classification ?? "—")}</TableCell>
                        <TableCell>
                          <Chip
                            label={String(item.reason_code ?? "")}
                            size="small"
                            color="warning"
                          />
                        </TableCell>
                        <TableCell>
                          {item.object_type === "dataset" && (
                            <Link
                              to={`/governance?request_type=DATASET_OWNERSHIP&object_id=${String(item.object_id)}&dataset_id=${String(item.object_id)}`}
                            >
                              Governance
                            </Link>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            </CardContent>
          </Card>
        </Stack>
      )}
    </AnalyticsShell>
  );
}
