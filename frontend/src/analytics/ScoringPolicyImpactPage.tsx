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
  TextField,
  Typography,
} from "@mui/material";
import { Link } from "react-router-dom";
import { AnalyticsShell } from "./AnalyticsShell";
import { AnalyticsApiError, fetchScoringPolicyImpact, type AnalyticsEnvelope } from "./api";
import {
  scoringPolicyImpactSummaryFromApi,
  type AnalyticsPageState,
  type ScoringPolicyImpactSummary,
} from "./model";

function KpiCard({ title, value }: { title: string; value: string }) {
  return (
    <Card sx={{ minWidth: 150, flex: 1 }}>
      <CardContent>
        <Typography variant="caption" color="text.secondary">{title}</Typography>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>{value}</Typography>
      </CardContent>
    </Card>
  );
}

export function ScoringPolicyImpactPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [state, setState] = useState<AnalyticsPageState>("loading");
  const [data, setData] = useState<AnalyticsEnvelope | null>(null);
  const [summary, setSummary] = useState<ScoringPolicyImpactSummary | null>(null);
  const [correlationId, setCorrelationId] = useState<string>();

  const baselineVersion = searchParams.get("baseline_version") ?? "";
  const candidateVersion = searchParams.get("candidate_version") ?? "";

  const load = useCallback(async (signal?: AbortSignal) => {
    setState("loading");
    try {
      const response = await fetchScoringPolicyImpact(
        {
          startDate: searchParams.get("start_date") ?? undefined,
          endDate: searchParams.get("end_date") ?? undefined,
          sourceId: searchParams.get("source_id") ?? undefined,
          datasetId: searchParams.get("dataset_id") ?? undefined,
        },
        {
          baselineVersion: baselineVersion || undefined,
          candidateVersion: candidateVersion || undefined,
        },
        signal,
      );
      if (signal?.aborted) return;
      setData(response);
      setCorrelationId(response.correlation_id);
      setSummary(scoringPolicyImpactSummaryFromApi(response.summary));
      setState("normal");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof AnalyticsApiError) {
        setCorrelationId(error.correlationId);
        setState(error.kind === "forbidden" || error.kind === "unauthorized" ? "unauthorized" : "error");
      } else setState("error");
    }
  }, [searchParams, baselineVersion, candidateVersion]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const handleVersionChange = useCallback(
    (key: string, value: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (value) next.set(key, value);
        else next.delete(key);
        return next;
      });
    },
    [setSearchParams],
  );

  return (
    <AnalyticsShell activeTab="scoring-policy" state={state} correlationId={correlationId}>
      {state === "loading" && (
        <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
          <CircularProgress aria-label="Yukleniyor" />
        </Box>
      )}
      {state === "error" && (
        <Alert severity="error"><Typography>Politika etki verisi yuklenemedi.</Typography></Alert>
      )}
      {state === "normal" && summary && (
        <Stack spacing={3}>
          {/* Version selectors */}
          <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
            <TextField
              label="Baseline Surum"
              size="small"
              value={baselineVersion}
              onChange={(e) => handleVersionChange("baseline_version", e.target.value)}
              placeholder={summary.activeVersion ?? "aktif"}
              sx={{ minWidth: 200 }}
            />
            <TextField
              label="Candidate Surum"
              size="small"
              value={candidateVersion}
              onChange={(e) => handleVersionChange("candidate_version", e.target.value)}
              sx={{ minWidth: 200 }}
            />
          </Stack>

          {/* Summary KPIs */}
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", gap: 1 }}>
            <KpiCard title="Iyilesen" value={String(summary.improvedCount)} />
            <KpiCard title="Kotulesen" value={String(summary.deterioratedCount)} />
            <KpiCard title="Degismeyen" value={String(summary.unchangedCount)} />
            <KpiCard title="Seviye Degisen" value={String(summary.levelChangedCount)} />
            <KpiCard title="Simule Edilemeyen" value={String(summary.notSimulatableCount)} />
          </Stack>

          {/* Simulation warning */}
          <Alert severity="info">
            <Typography variant="body2">
              Simule sonuclar tahmindir ve gercek skor yayini degildir.
              Aktif konfigurasyon degisikligi governance onayi gerektirir.
            </Typography>
          </Alert>

          {/* Configuration diff */}
          {data?.breakdowns?.configuration_diff ? (
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
                  Konfigurasyon Farki
                </Typography>
                <Box sx={{ overflowX: "auto" }}>
                  <Table size="small" aria-label="Konfigurasyon fark tablosu">
                    <TableHead>
                      <TableRow>
                        <TableCell>Parametre</TableCell>
                        <TableCell>Onceki</TableCell>
                        <TableCell>Sonraki</TableCell>
                        <TableCell>Delta</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.entries(
                        (data.breakdowns.configuration_diff as Record<string, unknown>).thresholds as Record<string, { before: number; after: number; delta: number }> ?? {},
                      ).map(([key, val]) => (
                        <TableRow key={key}>
                          <TableCell>{key}</TableCell>
                          <TableCell>{val.before?.toFixed(2) ?? "\u2014"}</TableCell>
                          <TableCell>{val.after?.toFixed(2) ?? "\u2014"}</TableCell>
                          <TableCell>
                            <Chip
                              label={(val.delta ?? 0).toFixed(2)}
                              size="small"
                              color={val.delta > 0 ? "success" : val.delta < 0 ? "error" : "default"}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Box>
              </CardContent>
            </Card>
          ) : null}

          {/* Most affected scopes */}
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
                En Cok Etkilenen Kapsamlar
              </Typography>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small" aria-label="Politika etki tablosu">
                  <TableHead>
                    <TableRow>
                      <TableCell>Kapsam</TableCell>
                      <TableCell>Mevcut Skor</TableCell>
                      <TableCell>Mevcut Seviye</TableCell>
                      <TableCell>Simule Skor</TableCell>
                      <TableCell>Simule Seviye</TableCell>
                      <TableCell>Delta</TableCell>
                      <TableCell>Kanit</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data?.items.slice(0, 50).map((item, idx) => (
                      <TableRow key={idx}>
                        <TableCell>{`${String(item.scope_type ?? "")}:${String(item.scope_id ?? "").slice(0, 8)}`}</TableCell>
                        <TableCell>
                          {item.current_score !== null && item.current_score !== undefined
                            ? Number(item.current_score).toFixed(2)
                            : "—"}
                        </TableCell>
                        <TableCell>{String(item.current_level ?? "—")}</TableCell>
                        <TableCell>
                          {item.simulated_score !== null && item.simulated_score !== undefined
                            ? Number(item.simulated_score).toFixed(2)
                            : "—"}
                        </TableCell>
                        <TableCell>{String(item.simulated_level ?? "—")}</TableCell>
                        <TableCell>
                          {item.delta !== null && item.delta !== undefined ? (
                            <Chip
                              label={Number(item.delta).toFixed(2)}
                              size="small"
                              color={Number(item.delta) > 0 ? "success" : Number(item.delta) < 0 ? "error" : "default"}
                            />
                          ) : (
                            "—"
                          )}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={String(item.evidence_class ?? "")}
                            size="small"
                            variant="outlined"
                            color={String(item.evidence_class) === "OBSERVED" ? "primary" : "default"}
                          />
                          {item.reason_code !== "COMPARABLE" && (
                            <Chip
                              label={String(item.reason_code ?? "")}
                              size="small"
                              sx={{ ml: 0.5 }}
                            />
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            </CardContent>
          </Card>

          {/* Governance link */}
          <Alert severity="info">
            <Typography variant="body2">
              Konfigurasyonu aktifleştirmek icin{" "}
              <Link to="/governance">Yonetisim Gorevleri</Link> sayfasindan talep olusturun.
            </Typography>
          </Alert>
        </Stack>
      )}
    </AnalyticsShell>
  );
}
