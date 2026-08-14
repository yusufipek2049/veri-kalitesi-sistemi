import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { Link } from "react-router-dom";
import { fetchScores, ScoreApiError } from "./api";
import { scoresFromApi, type ScoreListItem, type ScoreState } from "./model";
import { AppShell } from "../components/AppShell";
import { fetchRules } from "../rules/api";
import type { RuleListApiResponse } from "../rules/model";
import { listCatalogDatasets } from "../catalog/api";

const scopeLabel: Record<string, string> = {
  RULE: "Kural",
  DATASET: "Veri Kümesi",
  DIMENSION: "Boyut",
  SOURCE: "Kaynak",
  ENTERPRISE: "Kurum",
};

const statusColor = (status: string): "success" | "warning" | "error" | "default" => {
  switch (status) {
    case "CALCULATED":
      return "success";
    case "PARTIAL":
      return "warning";
    case "NOT_CALCULATED":
    case "NOT_CALCULATED_TECHNICAL_ERROR":
    case "CONFIG_ERROR":
      return "error";
    default:
      return "default";
  }
};

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

interface RuleOption {
  id: string;
  label: string;
  code: string;
}

interface DatasetOption {
  id: string;
  label: string;
}

export function ScoresPage() {
  const [state, setState] = useState<ScoreState>("loading");
  const [scores, setScores] = useState<ScoreListItem[]>([]);
  const [errorKind, setErrorKind] = useState<string | null>(null);

  // Filter state
  const [scopeType, setScopeType] = useState<string>("");
  const [scopeId, setScopeId] = useState<string>("");
  const [scoreStatus, setScoreStatus] = useState<string>("");
  const [periodStart, setPeriodStart] = useState<string>("");
  const [periodEnd, setPeriodEnd] = useState<string>("");

  // Autocomplete options
  const [ruleOptions, setRuleOptions] = useState<RuleOption[]>([]);
  const [datasetOptions, setDatasetOptions] = useState<DatasetOption[]>([]);
  const [selectedRule, setSelectedRule] = useState<RuleOption | null>(null);
  const [selectedDataset, setSelectedDataset] = useState<DatasetOption | null>(null);

  // Load rules and datasets for autocomplete
  useEffect(() => {
    const controller = new AbortController();
    const loadOptions = async () => {
      try {
        const [rulesResp, datasetsResp] = await Promise.all([
          fetchRules(controller.signal),
          listCatalogDatasets({ limit: 200 }),
        ]);
        const rules = (rulesResp as RuleListApiResponse).items.map((r) => ({
          id: r.quality_rule_id,
          label: `${r.code} — ${r.name}`,
          code: r.code,
        }));
        setRuleOptions(rules);
        const datasets = datasetsResp.items.map((d) => ({
          id: d.dataset_id,
          label: `${d.namespace}.${d.name}`,
        }));
        setDatasetOptions(datasets);
      } catch {
        // Silently fail — autocomplete will be empty
      }
    };
    void loadOptions();
    return () => controller.abort();
  }, []);

  // Resolve scope_id from autocomplete selection
  useEffect(() => {
    if (scopeType === "RULE" && selectedRule) {
      setScopeId(selectedRule.id);
    } else if (scopeType === "DATASET" && selectedDataset) {
      setScopeId(selectedDataset.id);
    } else if (scopeType && scopeType !== "RULE" && scopeType !== "DATASET") {
      // For SOURCE, DIMENSION, ENTERPRISE — free text
    } else if (!scopeType) {
      setScopeId("");
      setSelectedRule(null);
      setSelectedDataset(null);
    }
  }, [scopeType, selectedRule, selectedDataset]);

  const load = useCallback(
    async (signal: AbortSignal) => {
      setState("loading");
      setErrorKind(null);
      try {
        const response = await fetchScores(
          {
            limit: 200,
            scopeType: scopeType || undefined,
            scopeId: scopeId || undefined,
            scoreStatus: scoreStatus || undefined,
            periodStart: periodStart || undefined,
            periodEnd: periodEnd || undefined,
          },
          signal,
        );
        const items = scoresFromApi(response);
        if (items.length === 0) {
          setState("empty");
        } else {
          setScores(items);
          setState("normal");
        }
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
    [scopeType, scopeId, scoreStatus, periodStart, periodEnd],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  // Compute trend for rule scores (last N scores per scope_id)
  const trendByScopeId = useMemo(() => {
    const grouped = new Map<string, ScoreListItem[]>();
    for (const s of scores) {
      if (s.scopeType === "RULE" && s.scopeId) {
        const key = s.scopeId;
        if (!grouped.has(key)) grouped.set(key, []);
        grouped.get(key)!.push(s);
      }
    }
    const result = new Map<string, number | null>();
    for (const [key, items] of grouped) {
      if (items.length < 2) {
        result.set(key, null);
        continue;
      }
      const sorted = [...items].sort(
        (a, b) => new Date(b.calculatedAt).getTime() - new Date(a.calculatedAt).getTime(),
      );
      const latest = sorted[0]?.scoreValue;
      const previous = sorted[1]?.scoreValue;
      if (latest != null && previous != null) {
        result.set(key, latest - previous);
      } else {
        result.set(key, null);
      }
    }
    return result;
  }, [scores]);

  // Resolve rule code/name from scopeDisplayName or ruleOptions
  const ruleInfoMap = useMemo(() => {
    const map = new Map<string, { code: string; name: string }>();
    for (const r of ruleOptions) {
      map.set(r.id, { code: r.code, name: r.label });
    }
    return map;
  }, [ruleOptions]);

  // Resolve dataset name from datasetOptions
  const datasetNameMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const d of datasetOptions) {
      map.set(d.id, d.label);
    }
    return map;
  }, [datasetOptions]);

  const content = useMemo(() => {
    if (state === "loading") {
      return (
        <Box sx={{ alignItems: "center", display: "flex", justifyContent: "center", py: 10 }}>
          <CircularProgress aria-label="Skorlar yükleniyor" />
        </Box>
      );
    }
    if (state === "unauthorized") {
      return <Alert severity="warning">Bu sayfayı görüntüleme yetkiniz yok.</Alert>;
    }
    if (state === "error") {
      return <Alert severity="error">Skorlar yüklenemedi ({errorKind}).</Alert>;
    }
    if (state === "empty") {
      return <Alert severity="info">Filtre kriterlerine uygun skor bulunmuyor.</Alert>;
    }

    const isRuleScope = scopeType === "RULE";

    return (
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Skor ID</TableCell>
              <TableCell>Kapsam</TableCell>
              {isRuleScope && <TableCell>Kural</TableCell>}
              {isRuleScope && <TableCell>Dataset</TableCell>}
              <TableCell>Değer</TableCell>
              <TableCell>Seviye</TableCell>
              <TableCell>Durum</TableCell>
              {isRuleScope && <TableCell>Trend</TableCell>}
              <TableCell>Yayın</TableCell>
              <TableCell>Hesaplama</TableCell>
              <TableCell>Detay</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {scores.map((score) => {
              const ruleInfo =
                isRuleScope && score.scopeId ? ruleInfoMap.get(score.scopeId) : undefined;
              const datasetName =
                isRuleScope && score.scopeId
                  ? datasetNameMap.get(score.scopeId)
                  : undefined;
              const trend =
                isRuleScope && score.scopeId
                  ? trendByScopeId.get(score.scopeId)
                  : undefined;

              return (
                <TableRow key={score.id} hover>
                  <TableCell>
                    <Link to={`/scores/${score.id}`}>{score.id.slice(0, 8)}…</Link>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={scopeLabel[score.scopeType] ?? score.scopeType}
                      size="small"
                    />
                    {score.scopeDisplayName ? (
                      <Box sx={{ ml: 0.5, display: "inline" }}>
                        {score.scopeType === "DATASET" && score.scopeId ? (
                          <Link to={`/catalog/datasets/${score.scopeId}`}>
                            {score.scopeDisplayName}
                          </Link>
                        ) : (
                          score.scopeDisplayName
                        )}
                        {score.scopeParentName && (
                          <Typography
                            component="div"
                            variant="caption"
                            color="text.secondary"
                            sx={{ lineHeight: 1.2 }}
                          >
                            {score.scopeParentName}
                          </Typography>
                        )}
                      </Box>
                    ) : score.scopeId ? (
                      ` ${score.scopeId.slice(0, 8)}`
                    ) : null}
                  </TableCell>
                  {isRuleScope && (
                    <TableCell>
                      {ruleInfo ? (
                        <Box>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            {ruleInfo.code}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {ruleInfo.name}
                          </Typography>
                        </Box>
                      ) : (
                        score.scopeDisplayName ?? "—"
                      )}
                    </TableCell>
                  )}
                  {isRuleScope && (
                    <TableCell>
                      {datasetName ?? score.scopeParentName ?? "—"}
                    </TableCell>
                  )}
                  <TableCell sx={{ fontVariantNumeric: "tabular-nums" }}>
                    {score.scoreValue !== null ? score.scoreValue.toFixed(2) : "—"}
                  </TableCell>
                  <TableCell>
                    {score.level ? (
                      <Chip color={levelColor(score.level)} label={score.level} size="small" />
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip
                      color={statusColor(score.scoreStatus)}
                      label={score.scoreStatus}
                      size="small"
                    />
                  </TableCell>
                  {isRuleScope && (
                    <TableCell sx={{ fontVariantNumeric: "tabular-nums" }}>
                      {trend != null ? (
                        <Typography
                          variant="body2"
                          color={trend >= 0 ? "success.main" : "error.main"}
                          sx={{ fontWeight: 500 }}
                        >
                          {trend >= 0 ? "▲" : "▼"} {Math.abs(trend).toFixed(2)}
                        </Typography>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                  )}
                  <TableCell>{score.publicationId ? "Yayında" : "—"}</TableCell>
                  <TableCell>{new Date(score.calculatedAt).toLocaleString("tr-TR")}</TableCell>
                  <TableCell>
                    <Link to={`/scores/${score.id}`}>Detay</Link>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    );
  }, [
    state,
    scores,
    errorKind,
    scopeType,
    ruleInfoMap,
    datasetNameMap,
    trendByScopeId,
  ]);

  return (
    <AppShell currentPage="Skorlar">
      <Stack sx={{ gap: 4, p: { md: 4, lg: 6 } }}>
        <Stack direction="row" sx={{ alignItems: "center", justifyContent: "space-between" }}>
          <Typography variant="h4">Skorlar</Typography>
          <Button
            component={Link}
            to="/scores/comparison"
            variant="outlined"
            size="small"
          >
            Karşılaştır
          </Button>
        </Stack>

        {/* Filter Controls */}
        <Paper variant="outlined" sx={{ borderRadius: 1.5, p: 3 }}>
          <Stack direction="row" sx={{ flexWrap: "wrap", gap: 2, alignItems: "flex-end" }}>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="scope-type-label">Kapsam Tipi</InputLabel>
              <Select
                labelId="scope-type-label"
                label="Kapsam Tipi"
                value={scopeType}
                onChange={(e) => setScopeType(e.target.value)}
              >
                <MenuItem value="">Tümü</MenuItem>
                <MenuItem value="RULE">Kural</MenuItem>
                <MenuItem value="DATASET">Veri Kümesi</MenuItem>
                <MenuItem value="DIMENSION">Boyut</MenuItem>
                <MenuItem value="SOURCE">Kaynak</MenuItem>
                <MenuItem value="ENTERPRISE">Kurum</MenuItem>
              </Select>
            </FormControl>

            {scopeType === "RULE" && (
              <Autocomplete
                size="small"
                options={ruleOptions}
                value={selectedRule}
                onChange={(_, val) => setSelectedRule(val)}
                getOptionLabel={(opt) => opt.label}
                isOptionEqualToValue={(opt, val) => opt.id === val.id}
                sx={{ minWidth: 280 }}
                renderInput={(params) => (
                  <TextField {...params} label="Kural seçin" placeholder="Kural ara…" />
                )}
              />
            )}

            {scopeType === "DATASET" && (
              <Autocomplete
                size="small"
                options={datasetOptions}
                value={selectedDataset}
                onChange={(_, val) => setSelectedDataset(val)}
                getOptionLabel={(opt) => opt.label}
                isOptionEqualToValue={(opt, val) => opt.id === val.id}
                sx={{ minWidth: 280 }}
                renderInput={(params) => (
                  <TextField {...params} label="Dataset seçin" placeholder="Dataset ara…" />
                )}
              />
            )}

            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="status-label">Durum</InputLabel>
              <Select
                labelId="status-label"
                label="Durum"
                value={scoreStatus}
                onChange={(e) => setScoreStatus(e.target.value)}
              >
                <MenuItem value="">Tümü</MenuItem>
                <MenuItem value="CALCULATED">Hesaplandı</MenuItem>
                <MenuItem value="PARTIAL">Kısmi</MenuItem>
                <MenuItem value="NOT_CALCULATED">Hesaplanmadı</MenuItem>
                <MenuItem value="NOT_CALCULATED_TECHNICAL_ERROR">Teknik Hata</MenuItem>
                <MenuItem value="CONFIG_ERROR">Yapılandırma Hatası</MenuItem>
              </Select>
            </FormControl>

            <TextField
              size="small"
              label="Başlangıç"
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              sx={{ minWidth: 150 }}
            />

            <TextField
              size="small"
              label="Bitiş"
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              sx={{ minWidth: 150 }}
            />
          </Stack>
        </Paper>

        {content}
      </Stack>
    </AppShell>
  );
}
