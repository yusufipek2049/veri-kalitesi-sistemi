import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableFooter,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { ArrowLeft, ChevronDown } from "lucide-react";
import { fetchScoreDetail, ScoreApiError } from "./api";
import {
  scoreDetailFromApi,
  type ContributionGraphComponent,
  type ScoreDetail,
  type ScoreState,
} from "./model";
import { AppShell } from "../components/AppShell";
import { ScoreContributionPanel } from "../components/ScoreContributionPanel";

const levelColor = (level: string | null): "success" | "warning" | "error" | "default" => {
  switch (level) {
    case "GOOD":
      return "success";
    case "ACCEPTABLE":
      return "warning";
    case "RISKY":
    case "CRITICAL":
      return "error";
    default:
      return "default";
  }
};

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

const countLabels: Record<string, string> = {
  population: "Toplam popülasyon",
  eligible: "Uygun ölçüm",
  evaluated: "Değerlendirilen",
  passed: "Geçen",
  failed: "Kalan",
  excluded: "Dışlanan",
  technical_error: "Teknik hata",
  unknown: "Bilinmeyen",
};

function displayLabel(component: ContributionGraphComponent): string {
  return component.component_name ?? component.component_ref;
}

function contributionValue(component: ContributionGraphComponent): number | null {
  if (component.contribution === null) return null;
  const parsed = Number(component.contribution);
  return Number.isFinite(parsed) ? parsed : null;
}

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

  const includedComponents = useMemo(() => {
    const components = detail?.contributionGraph?.components ?? [];
    return components
      .filter((c) => c.included)
      .slice()
      .sort((a, b) => (contributionValue(b) ?? 0) - (contributionValue(a) ?? 0));
  }, [detail]);

  const excludedComponents = useMemo(
    () => (detail?.contributionGraph?.components ?? []).filter((c) => !c.included),
    [detail],
  );

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
  const rawScore = graph?.raw_quality_score ? Number(graph.raw_quality_score) : null;

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

  const countEntries = graph?.canonical_counts
    ? Object.entries(graph.canonical_counts).filter(([, value]) => value !== null)
    : [];

  return (
    <AppShell currentPage="Skor Detayı">
      <Stack sx={{ gap: 4, p: { md: 4, lg: 6 } }}>
        <Box sx={{ alignItems: "center", display: "flex", gap: 2 }}>
          <Button component={Link} startIcon={<ArrowLeft aria-hidden="true" size={16} />} to="/scores" variant="text">
            Skorlar
          </Button>
        </Box>

        {/* ── Temel Skor Bilgisi ── */}
        <Paper sx={{ p: 4, variant: "outlined" }}>
          <Box sx={{ alignItems: "center", display: "flex", flexWrap: "wrap", gap: 2 }}>
            <Typography sx={{ fontWeight: 800, fontVariantNumeric: "tabular-nums" }} variant="h2">
              {item.scoreValue !== null ? item.scoreValue.toFixed(2) : "—"}
            </Typography>
            {item.level ? (
              <Chip color={levelColor(item.level)} label={item.level} size="small" />
            ) : null}
            <Chip label={item.scoreStatus} size="small" variant="outlined" />
            {detail.publication ? (
              <Chip color="info" label={`Yayında · ${detail.publication.period}`} size="small" variant="outlined" />
            ) : null}
          </Box>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 4, mt: 3 }}>
            <Box>
              <Typography color="text.secondary" variant="caption">
                Kapsam
              </Typography>
              <Typography sx={{ fontWeight: 600 }}>
                {item.scopeDisplayName ?? item.scopeId ?? "—"}
              </Typography>
              {item.scopeParentName ? (
                <Typography color="text.secondary" variant="body2">
                  {item.scopeParentName}
                </Typography>
              ) : null}
            </Box>
            <Box>
              <Typography color="text.secondary" variant="caption">
                Kapsam tipi
              </Typography>
              <Typography sx={{ fontWeight: 600 }}>{item.scopeType}</Typography>
            </Box>
            <Box>
              <Typography color="text.secondary" variant="caption">
                Hesap zamanı
              </Typography>
              <Typography sx={{ fontWeight: 600 }}>
                {new Date(item.calculatedAt).toLocaleString("tr-TR")}
              </Typography>
            </Box>
            <Box>
              <Typography color="text.secondary" variant="caption">
                Ölçüm yeterliliği
              </Typography>
              <Typography sx={{ fontWeight: 600 }}>
                {graph?.measurement_qualification ?? item.measurementStatus ?? "—"}
              </Typography>
            </Box>
          </Box>
        </Paper>

        {/* ── Skoru Oluşturan Katkılar ── */}
        {includedComponents.length > 0 && (
          <Paper component="section" sx={{ p: 4, variant: "outlined" }}>
            <Typography component="h2" sx={{ mb: 1 }} variant="h3">
              Skoru Oluşturan Katkılar
            </Typography>
            <Typography color="text.secondary" sx={{ mb: 2 }} variant="body2">
              Hangi kuralın hangi ağırlıkla skora ne kadar katkı verdiği, toplam skorla
              birlikte aşağıdadır.
            </Typography>
            <TableContainer>
              <Table size="small" aria-label="Skoru oluşturan katkılar">
                <TableHead>
                  <TableRow>
                    <TableCell>Kural / Bileşen</TableCell>
                    <TableCell>Tip</TableCell>
                    <TableCell align="right">Kural skoru</TableCell>
                    <TableCell align="right">Ağırlık</TableCell>
                    <TableCell align="right">Katkı</TableCell>
                    <TableCell align="right">Pay</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {includedComponents.map((c) => {
                    const contribution = contributionValue(c);
                    const share =
                      contribution !== null && rawScore ? (contribution / rawScore) * 100 : null;
                    return (
                      <TableRow key={c.component_ref}>
                        <TableCell>
                          <Typography sx={{ fontWeight: 600 }} variant="body2">
                            {displayLabel(c)}
                          </Typography>
                          {c.component_name && c.component_name !== c.component_ref ? (
                            <Typography color="text.secondary" noWrap variant="caption">
                              {c.component_ref}
                            </Typography>
                          ) : null}
                        </TableCell>
                        <TableCell>{c.component_type}</TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                          {c.score ?? "—"}
                        </TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                          {c.weight ?? "—"}
                        </TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                          {contribution !== null ? contribution.toFixed(2) : "—"}
                        </TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                          {share !== null ? `%${share.toFixed(1)}` : "—"}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
                <TableFooter>
                  <TableRow>
                    <TableCell colSpan={4} sx={{ fontWeight: 700 }}>
                      Toplam skor
                    </TableCell>
                    <TableCell
                      align="right"
                      sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 700 }}
                    >
                      {graph?.raw_quality_score ?? item.scoreValue?.toFixed(2) ?? "—"}
                    </TableCell>
                    <TableCell align="right" sx={{ fontWeight: 700 }}>
                      %100
                    </TableCell>
                  </TableRow>
                </TableFooter>
              </Table>
            </TableContainer>
          </Paper>
        )}

        {/* ── Skor Katkı Grafiği ── */}
        {graph && <ScoreContributionPanel components={graph.components} />}

        {/* ── Dışlanan Bileşenler ── */}
        {excludedComponents.length > 0 && (
          <Paper component="section" sx={{ p: 4, variant: "outlined" }}>
            <Typography component="h2" sx={{ mb: 2 }} variant="h3">
              Skor Hesabına Dahil Edilmeyenler
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
                      <TableCell>{displayLabel(c)}</TableCell>
                      <TableCell>{c.component_type}</TableCell>
                      <TableCell>{c.exclusion_reason ?? "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        )}

        {/* ── Teknik Detaylar ── */}
        {graph && (
          <Accordion disableGutters variant="outlined">
            <AccordionSummary expandIcon={<ChevronDown aria-hidden="true" size={16} />}>
              <Typography sx={{ fontWeight: 700 }} variant="h3">
                Teknik Detaylar
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Stack sx={{ gap: 3 }}>
                {(calc || graph.versions) && (
                  <Box>
                    <Typography sx={{ fontWeight: 700, mb: 1 }} variant="subtitle2">
                      Hesaplama Parametreleri
                    </Typography>
                    <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1 }}>
                      {calc?.formula_version ? (
                        <Chip label={`Formül: ${String(calc.formula_version)}`} size="small" variant="outlined" />
                      ) : null}
                      {calc?.configuration_version ? (
                        <Chip label={`Konfigürasyon: ${String(calc.configuration_version)}`} size="small" variant="outlined" />
                      ) : null}
                      {calc?.weight_policy ? (
                        <Chip label={`Ağırlık politikası: ${String(calc.weight_policy)}`} size="small" variant="outlined" />
                      ) : null}
                      {Object.entries(graph.versions)
                        .filter(([, value]) => value !== null)
                        .map(([key, value]) => (
                          <Chip key={key} label={`${key}: ${value as string}`} size="small" variant="outlined" />
                        ))}
                    </Stack>
                  </Box>
                )}

                <Box>
                  <Typography sx={{ fontWeight: 700, mb: 1 }} variant="subtitle2">
                    Kritiklik Profili
                  </Typography>
                  <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1 }}>
                    {criticalityEntries.map((entry) => (
                      <Chip
                        color={critColor(entry.status)}
                        key={entry.label}
                        label={`${entry.label}: ${entry.status}`}
                        size="small"
                        variant="outlined"
                      />
                    ))}
                    {graph.critical_veto !== null && graph.critical_veto !== undefined && (
                      <Chip
                        color={graph.critical_veto ? "error" : "default"}
                        label={`Veto: ${graph.critical_veto ? "Evet" : "Hayır"}`}
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </Stack>
                </Box>

                {countEntries.length > 0 && (
                  <Box>
                    <Typography sx={{ fontWeight: 700, mb: 1 }} variant="subtitle2">
                      Ölçüm Sayaçları
                    </Typography>
                    <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1 }}>
                      {countEntries.map(([key, value]) => (
                        <Chip
                          key={key}
                          label={`${countLabels[key] ?? key}: ${value}`}
                          size="small"
                          variant="outlined"
                        />
                      ))}
                    </Stack>
                  </Box>
                )}

                <Box>
                  <Typography sx={{ fontWeight: 700, mb: 1 }} variant="subtitle2">
                    Kanıt ve Teşhis
                  </Typography>
                  <Typography color="text.secondary" variant="body2">
                    Kanıt referansları: {graph.evidence_references.length ? graph.evidence_references.join(", ") : "—"}
                  </Typography>
                  <Typography color="text.secondary" variant="body2">
                    Teşhis: {graph.diagnosis_status}
                    {graph.diagnosis_evidence_ref ? ` (${graph.diagnosis_evidence_ref})` : ""}
                  </Typography>
                  <Typography color="text.secondary" variant="body2">
                    Skor ID: {item.id}
                  </Typography>
                </Box>
              </Stack>
            </AccordionDetails>
          </Accordion>
        )}
      </Stack>
    </AppShell>
  );
}
