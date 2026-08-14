import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Divider,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { fetchScoreDetail, ScoreApiError } from "./api";
import { scoreDetailFromApi, type ScoreDetail, type ScoreState } from "./model";
import { AppShell } from "../components/AppShell";
import { ScoreContributionPanel } from "../components/ScoreContributionPanel";

export function ScoreDetailPage() {
  const { scoreId } = useParams<{ scoreId: string }>();
  const [state, setState] = useState<ScoreState>("loading");
  const [detail, setDetail] = useState<ScoreDetail | null>(null);
  const [errorKind, setErrorKind] = useState<string | null>(null);

  const load = useCallback(
    async (signal: AbortSignal) => {
      if (!scoreId) return;
      setState("loading");
      try {
        const response = await fetchScoreDetail(scoreId, signal);
        setDetail(scoreDetailFromApi(response));
        setState("normal");
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (error instanceof ScoreApiError) {
          if (error.kind === "unauthorized" || error.kind === "forbidden") {
            setState("unauthorized");
          } else {
            setErrorKind(error.kind);
            setState("error");
          }
        } else {
          setErrorKind("technical");
          setState("error");
        }
      }
    },
    [scoreId],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  if (state === "loading") {
    return (
      <AppShell currentPage="Skor Detayı">
        <Box sx={{ alignItems: "center", display: "flex", justifyContent: "center", py: 10 }}>
          <CircularProgress aria-label="Skor yükleniyor" />
        </Box>
      </AppShell>
    );
  }

  if (state === "unauthorized") {
    return (
      <AppShell currentPage="Skor Detayı">
        <Alert severity="warning">Bu skoru görüntüleme yetkiniz yok.</Alert>
      </AppShell>
    );
  }

  if (state === "error" || !detail) {
    return (
      <AppShell currentPage="Skor Detayı">
        <Alert severity="error">Skor yüklenemedi ({errorKind}).</Alert>
      </AppShell>
    );
  }

  const { item } = detail;
  const calc = detail.calculationDetails;
  const graph = detail.contributionGraph;
  const includedComponents = graph?.components.filter((c) => c.included) ?? [];
  const excludedComponents = graph?.components.filter((c) => !c.included) ?? [];

  const criticalityEntries: Array<{ label: string; status: string }> = graph
    ? [
        { label: "Kritik Kural", status: graph.critical_rule_status },
        { label: "Kritik Varlık", status: graph.critical_asset_status },
        { label: "Risk", status: graph.risk_status },
        { label: "SLA", status: graph.sla_status },
        { label: "Kapsam", status: graph.coverage_status },
        { label: "Kullanım Kararı", status: graph.usage_decision },
      ]
    : [];

  const critColor = (status: string): "success" | "warning" | "error" | "default" => {
    switch (status) {
      case "PASS":
      case "COMPLIANT":
      case "COVERED":
        return "success";
      case "WARNING":
      case "PARTIAL":
        return "warning";
      case "FAIL":
      case "CRITICAL":
      case "RISKY":
      case "NOT_COVERED":
        return "error";
      default:
        return "default";
    }
  };

  return (
    <AppShell currentPage="Skor Detayı">
      <Stack sx={{ gap: 4, p: { md: 4, lg: 6 } }}>
        <Typography variant="h4">Skor Detayı</Typography>

        {/* ── Temel Skor Bilgisi ── */}
        <Paper sx={{ p: 4, variant: "outlined" }}>
          <Stack sx={{ gap: 2 }}>
            <Typography variant="body2" color="text.secondary">Skor ID</Typography>
            <Typography variant="body1">{item.id}</Typography>
            <Typography variant="body2" color="text.secondary">Kapsam</Typography>
            <Typography variant="body1">
              <Chip label={item.scopeType} size="small" />
              {item.scopeId ? ` — ${item.scopeId}` : ""}
            </Typography>
            <Typography variant="body2" color="text.secondary">Değer / Seviye</Typography>
            <Typography variant="h5">
              {item.scoreValue !== null ? item.scoreValue.toFixed(2) : "—"}
              {item.level ? ` (${item.level})` : ""}
            </Typography>
            <Typography variant="body2" color="text.secondary">Durum</Typography>
            <Chip label={item.scoreStatus} size="small" />
            {detail.publication && (
              <>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>Yayın</Typography>
                <Typography variant="body1">
                  {detail.publication.period} — {detail.publication.status}
                </Typography>
              </>
            )}
          </Stack>
        </Paper>

        {/* ── Hesaplama Formülü ── */}
        {calc && (
          <Paper component="section" sx={{ p: 4, variant: "outlined" }}>
            <Typography component="h2" variant="h3" sx={{ mb: 3 }}>
              Hesaplama Formülü
            </Typography>
            <Stack sx={{ gap: 2 }}>
              {Boolean(calc.formula_version) && (
                <Box>
                  <Typography variant="body2" color="text.secondary">Formul Sürümü</Typography>
                  <Typography variant="body1">{String(calc.formula_version)}</Typography>
                </Box>
              )}
              {Boolean(calc.configuration_version) && (
                <Box>
                  <Typography variant="body2" color="text.secondary">Konfigürasyon Sürümü</Typography>
                  <Typography variant="body1">{String(calc.configuration_version)}</Typography>
                </Box>
              )}
              {Boolean(calc.weight_policy) && (
                <Box>
                  <Typography variant="body2" color="text.secondary">Ağırlık Politikası</Typography>
                  <Typography variant="body1">{String(calc.weight_policy)}</Typography>
                </Box>
              )}
              {graph?.versions && (
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Sürüm Bilgileri
                  </Typography>
                  <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1 }}>
                    {Object.entries(graph.versions)
                      .filter(([, v]) => v !== null)
                      .map(([key, value]) => (
                        <Chip
                          key={key}
                          label={`${key}: ${value as string}`}
                          size="small"
                          variant="outlined"
                        />
                      ))}
                  </Stack>
                </Box>
              )}
            </Stack>
          </Paper>
        )}

        {/* ── Skor Katkı Grafiği ── */}
        {graph && (
          <ScoreContributionPanel
            components={graph.components}
            profileVersion={graph.versions?.profile_version}
            evidenceReferences={graph.evidence_references}
            diagnosisStatus={graph.diagnosis_status}
            diagnosisEvidenceRef={graph.diagnosis_evidence_ref}
          />
        )}

        {/* ── Dahil Edilen Bileşenler ── */}
        {includedComponents.length > 0 && (
          <Paper component="section" sx={{ p: 4, variant: "outlined" }}>
            <Typography component="h2" variant="h3" sx={{ mb: 2 }}>
              Dahil Edilen Bileşenler
            </Typography>
            <TableContainer>
              <Table size="small" aria-label="Dahil edilen bileşenler">
                <TableHead>
                  <TableRow>
                    <TableCell>Bileşen</TableCell>
                    <TableCell>Tip</TableCell>
                    <TableCell align="right">Skor</TableCell>
                    <TableCell align="right">Ağırlık</TableCell>
                    <TableCell align="right">Katkı</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {includedComponents.map((c) => (
                    <TableRow key={c.component_ref}>
                      <TableCell>{c.component_ref}</TableCell>
                      <TableCell>{c.component_type}</TableCell>
                      <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                        {c.score ?? "—"}
                      </TableCell>
                      <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                        {c.weight ?? "—"}
                      </TableCell>
                      <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                        {c.contribution ?? "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        )}

        {/* ── Dışlanan Bileşenler ── */}
        {excludedComponents.length > 0 && (
          <Paper component="section" sx={{ p: 4, variant: "outlined" }}>
            <Typography component="h2" variant="h3" sx={{ mb: 2 }}>
              Dışlanan Bileşenler
            </Typography>
            <TableContainer>
              <Table size="small" aria-label="Dışlanan bileşenler">
                <TableHead>
                  <TableRow>
                    <TableCell>Bileşen</TableCell>
                    <TableCell>Tip</TableCell>
                    <TableCell>Dışlama Nedeni</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {excludedComponents.map((c) => (
                    <TableRow key={c.component_ref}>
                      <TableCell>{c.component_ref}</TableCell>
                      <TableCell>{c.component_type}</TableCell>
                      <TableCell>{c.exclusion_reason ?? "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        )}

        {/* ── Kritiklik Profili ── */}
        {graph && (
          <Paper component="section" sx={{ p: 4, variant: "outlined" }}>
            <Typography component="h2" variant="h3" sx={{ mb: 2 }}>
              Kritiklik Profili
            </Typography>
            <Stack direction="row" sx={{ flexWrap: "wrap", gap: 2 }}>
              {criticalityEntries.map((entry) => (
                <Chip
                  key={entry.label}
                  label={`${entry.label}: ${entry.status}`}
                  color={critColor(entry.status)}
                  size="small"
                  variant="outlined"
                />
              ))}
              {graph.critical_veto !== null && graph.critical_veto !== undefined && (
                <Chip
                  label={`Veto: ${graph.critical_veto ? "Evet" : "Hayır"}`}
                  color={graph.critical_veto ? "error" : "default"}
                  size="small"
                  variant="outlined"
                />
              )}
            </Stack>
            {graph.evidence_references.length > 0 && (
              <Box sx={{ mt: 3 }}>
                <Divider sx={{ mb: 2 }} />
                <Typography variant="body2" color="text.secondary">
                  Kanıt Referansları: {graph.evidence_references.join(", ")}
                </Typography>
              </Box>
            )}
          </Paper>
        )}
      </Stack>
    </AppShell>
  );
}
