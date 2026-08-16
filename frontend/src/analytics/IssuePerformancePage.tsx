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
import { AnalyticsApiError, fetchIssuePerformance, type AnalyticsEnvelope } from "./api";
import {
  formatDuration,
  formatRatio,
  issuePerformanceSummaryFromApi,
  ratioTooltip,
  type AnalyticsPageState,
  type IssuePerformanceSummary,
} from "./model";

function KpiCard({ title, value, tooltip }: { title: string; value: string; tooltip?: string }) {
  return (
    <Card sx={{ minWidth: 150, flex: 1 }}>
      <CardContent>
        <Typography variant="caption" color="text.secondary">{title}</Typography>
        <Tooltip title={tooltip ?? ""}>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>{value}</Typography>
        </Tooltip>
      </CardContent>
    </Card>
  );
}

export function IssuePerformancePage() {
  const [searchParams] = useSearchParams();
  const [state, setState] = useState<AnalyticsPageState>("loading");
  const [data, setData] = useState<AnalyticsEnvelope | null>(null);
  const [summary, setSummary] = useState<IssuePerformanceSummary | null>(null);
  const [correlationId, setCorrelationId] = useState<string>();

  const load = useCallback(async (signal?: AbortSignal) => {
    setState("loading");
    try {
      const response = await fetchIssuePerformance(
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
      setSummary(issuePerformanceSummaryFromApi(response.summary));
      setState(response.items.length > 0 || summary?.openIssueCount ? "normal" : "empty");
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
    <AnalyticsShell activeTab="issues" state={state} correlationId={correlationId}>
      {state === "loading" && (
        <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
          <CircularProgress aria-label="Yukleniyor" />
        </Box>
      )}
      {state === "error" && (
        <Alert severity="error"><Typography>Issue performans verisi yuklenemedi.</Typography></Alert>
      )}
      {state === "empty" && (
        <Alert severity="info"><Typography>Gosterilecek issue verisi bulunamadi.</Typography></Alert>
      )}
      {state === "normal" && summary && (
        <Stack spacing={3}>
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", gap: 1 }}>
            <KpiCard title="Acik Issue" value={String(summary.openIssueCount)} />
            <KpiCard title="Kritik Acik" value={String(summary.criticalOpenCount)} />
            <KpiCard
              title="MTTA p50"
              value={formatDuration(summary.mttaP50)}
              tooltip={`Orneklem: ${summary.mttaSampleCount}`}
            />
            <KpiCard
              title="MTTA p95"
              value={formatDuration(summary.mttaP95)}
              tooltip={`Orneklem: ${summary.mttaSampleCount}`}
            />
            <KpiCard
              title="MTTR p50"
              value={formatDuration(summary.mttrP50)}
              tooltip={`Orneklem: ${summary.mttrSampleCount}`}
            />
            <KpiCard
              title="MTTR p95"
              value={formatDuration(summary.mttrP95)}
              tooltip={`Orneklem: ${summary.mttrSampleCount}`}
            />
            <KpiCard title="Cozulmemis" value={String(summary.unresolvedCount)} />
            <KpiCard
              title="Dogrulama Basarisi"
              value={formatRatio(summary.verificationSuccessRate)}
              tooltip={ratioTooltip(summary.verificationSuccessRate)}
            />
            <KpiCard title="Tekrarlayan" value={String(summary.recurringIssueCount)} />
          </Stack>

          {/* Age distribution */}
          {data?.breakdowns?.by_age_bucket ? (
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 1, fontWeight: 700 }}>
                  Yas Dagilimi
                </Typography>
                <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 0.5 }}>
                  {Object.entries(data.breakdowns.by_age_bucket as Record<string, number>).map(
                    ([bucket, count]) => (
                      <Chip key={bucket} label={`${bucket} gun: ${count as number}`} size="small" variant="outlined" />
                    ),
                  )}
                </Stack>
              </CardContent>
            </Card>
          ) : null}

          {/* Oldest / most recurring issues */}
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
                En Yasli ve Tekrarlayan Issue'lar
              </Typography>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small" aria-label="Issue performans tablosu">
                  <TableHead>
                    <TableRow>
                      <TableCell>Issue</TableCell>
                      <TableCell>Kapsam</TableCell>
                      <TableCell>Durum</TableCell>
                      <TableCell>Oncelik</TableCell>
                      <TableCell>Yas</TableCell>
                      <TableCell>MTTA</TableCell>
                      <TableCell>MTTR</TableCell>
                      <TableCell>Tekrar</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data?.items.slice(0, 50).map((item, idx) => (
                      <TableRow key={String(item.issue_id ?? idx)}>
                        <TableCell>
                          <Link to={`/issues?issue_id=${String(item.issue_id)}`}>
                            {String(item.issue_id).slice(0, 8)}...
                          </Link>
                        </TableCell>
                        <TableCell>
                          <Chip label={String(item.scope_type ?? "")} size="small" />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={String(item.status ?? "")}
                            size="small"
                            color={
                              ["NEW", "ASSIGNED", "INVESTIGATING"].includes(String(item.status))
                                ? "warning"
                                : "default"
                            }
                          />
                        </TableCell>
                        <TableCell>{String(item.priority ?? "")}</TableCell>
                        <TableCell>{formatDuration(item.age_seconds as number | null)}</TableCell>
                        <TableCell>{formatDuration(item.time_to_ack_seconds as number | null)}</TableCell>
                        <TableCell>{formatDuration(item.time_to_resolve_seconds as number | null)}</TableCell>
                        <TableCell>{String(item.recurrence_count ?? 0)}</TableCell>
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
