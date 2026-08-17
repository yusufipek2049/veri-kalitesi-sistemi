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
import { AnalyticsApiError, fetchRuleHealth, type AnalyticsEnvelope } from "./api";
import {
  formatRatio,
  ratioTooltip,
  ruleHealthSummaryFromApi,
  type AnalyticsPageState,
  type RuleHealthSummary,
} from "./model";

function KpiCard({ title, value, tooltip }: { title: string; value: string; tooltip?: string }) {
  return (
    <Card sx={{ minWidth: 180, flex: 1 }}>
      <CardContent>
        <Typography variant="caption" color="text.secondary">
          {title}
        </Typography>
        <Tooltip title={tooltip ?? ""}>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            {value}
          </Typography>
        </Tooltip>
      </CardContent>
    </Card>
  );
}

export function RuleHealthPage() {
  const [searchParams] = useSearchParams();
  const [state, setState] = useState<AnalyticsPageState>("loading");
  const [data, setData] = useState<AnalyticsEnvelope | null>(null);
  const [summary, setSummary] = useState<RuleHealthSummary | null>(null);
  const [correlationId, setCorrelationId] = useState<string>();

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setState("loading");
      try {
        const response = await fetchRuleHealth(
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
        setSummary(ruleHealthSummaryFromApi(response.summary));
        setState(response.items.length > 0 || (response.summary as Record<string, unknown>).active_rule_count ? "normal" : "empty");
      } catch (error) {
        if (signal?.aborted) return;
        if (error instanceof AnalyticsApiError) {
          setCorrelationId(error.correlationId);
          setState(error.kind === "forbidden" || error.kind === "unauthorized" ? "unauthorized" : "error");
        } else {
          setState("error");
        }
      }
    },
    [searchParams],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  return (
    <AnalyticsShell activeTab="rule-health" state={state} correlationId={correlationId}>
      {state === "loading" && (
        <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
          <CircularProgress aria-label="Yükleniyor" />
        </Box>
      )}

      {state === "error" && (
        <Alert severity="error">
          <Typography>Kural sağlığı verisi yüklenemedi.</Typography>
          {correlationId && (
            <Typography variant="caption">Correlation: {correlationId}</Typography>
          )}
        </Alert>
      )}

      {state === "empty" && (
        <Alert severity="info">
          <Typography>Gösterilecek kural sağlığı verisi bulunamadı.</Typography>
        </Alert>
      )}

      {state === "normal" && summary && (
        <Stack spacing={3}>
          {/* KPI cards */}
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", gap: 1 }}>
            <KpiCard
              title="Dataset Kapsamı"
              value={formatRatio(summary.datasetCoverage)}
              tooltip={ratioTooltip(summary.datasetCoverage)}
            />
            <KpiCard
              title="Alan Kapsamı"
              value={formatRatio(summary.fieldCoverage)}
              tooltip={ratioTooltip(summary.fieldCoverage)}
            />
            <KpiCard
              title="Kritik Kapsam"
              value={formatRatio(summary.criticalCoverage)}
              tooltip={ratioTooltip(summary.criticalCoverage)}
            />
            <KpiCard
              title="Hiç Çalışmamış"
              value={String(summary.neverExecutedCount)}
            />
            <KpiCard
              title="Dalgalı Kurallar"
              value={String(summary.flakyRuleCount)}
            />
          </Stack>

          {/* Risky rules table */}
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
                Güvenilmez / Dalgalı Kurallar
              </Typography>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small" aria-label="Riskli kurallar tablosu">
                  <TableHead>
                    <TableRow>
                      <TableCell>Kod</TableCell>
                      <TableCell>Dataset</TableCell>
                      <TableCell>Boyut</TableCell>
                      <TableCell>Kritiklik</TableCell>
                      <TableCell>Son Skor</TableCell>
                      <TableCell>Teknik Hata</TableCell>
                      <TableCell>Durum</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data?.items.slice(0, 50).map((item, idx) => (
                      <TableRow key={String(item.quality_rule_id ?? idx)}>
                        <TableCell>
                          {String(item.code ?? "")}
                        </TableCell>
                        <TableCell>
                          {item.dataset_id ? (
                            <Link to={`/catalog/datasets/${String(item.dataset_id)}`}>
                              {String(item.dataset_name ?? item.dataset_id)}
                            </Link>
                          ) : (
                            "—"
                          )}
                        </TableCell>
                        <TableCell>{String(item.dimension ?? "—")}</TableCell>
                        <TableCell>{String(item.criticality ?? "—")}</TableCell>
                        <TableCell>
                          {item.last_score_value !== null && item.last_score_value !== undefined
                            ? Number(item.last_score_value).toFixed(2)
                            : "—"}
                        </TableCell>
                        <TableCell>{String(item.technical_error_count ?? 0)}</TableCell>
                        <TableCell>
                          <Chip
                            label={String(item.reason_code ?? "OK")}
                            size="small"
                            color={
                              item.reason_code === "OK"
                                ? "success"
                                : item.reason_code === "NEVER_EXECUTED" || item.reason_code === "NO_VERSION"
                                  ? "warning"
                                  : "error"
                            }
                          />
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
