import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  useTheme,
} from "@mui/material";
import { LineChart, ScatterChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsCoreOption } from "echarts/core";
import { Search } from "lucide-react";
import { Link } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { designTokens } from "../theme/tokens";
import { listCatalogDatasets } from "../catalog/api";
import { fetchDataSources } from "../dataSources/api";
import { fetchScores } from "../scores/api";
import { scoresFromApi, type ScoreListItem } from "../scores/model";
import { DashboardApiError, fetchDashboardOverview } from "./api";
import { overviewFromApi, type DashboardOverview, type DashboardScoreNode, type DashboardState } from "./model";
import { createTrendTooltipFormatter } from "./trendTooltip";

echarts.use([LineChart, ScatterChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

type TrendWindow = "7g" | "14g" | "30g";

const trendWindowDays: Record<TrendWindow, number> = {
  "7g": 7,
  "14g": 14,
  "30g": 30,
};

const trendWindowLabels: Record<TrendWindow, string> = {
  "7g": "Son 7 gün",
  "14g": "Son 14 gün",
  "30g": "Son 30 gün",
};

const levelColor = (level: string | null): "success" | "warning" | "error" | "default" => {
  switch (level) {
    case "GOOD": return "success";
    case "ACCEPTABLE": return "warning";
    case "RISKY":
    case "CRITICAL": return "error";
    default: return "default";
  }
};

const statusLabel: Record<string, string> = {
  CALCULATED: "Hesaplandı",
  NOT_CALCULATED: "Hesaplanmadı",
  NO_DATA: "Veri yok",
  PARTIAL: "Kısmi",
  NOT_CALCULATED_TECHNICAL_ERROR: "Teknik hata",
  CONFIG_ERROR: "Yapılandırma hatası",
};

const qualificationLabel: Record<string, string> = {
  NO_DATA: "Veri yok",
  VALIDATION_REQUIRED: "Doğrulama gerekli",
  TECHNICAL_FAILURE: "Teknik hata",
};

function formatScore(value: number | null): string {
  if (value === null) return "—";
  return value.toFixed(1);
}

function formatChange(value: number | null): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}`;
}

// ── KPI Card ──

interface KpiCardProps {
  label: string;
  value: string;
  subtitle?: string;
  tone?: "success" | "warning" | "error" | "technical" | "default";
}

function KpiCard({ label, value, subtitle, tone = "default" }: KpiCardProps) {
  const theme = useTheme();
  const toneColor = tone === "technical"
    ? theme.status.technical
    : tone === "success"
      ? theme.status.success
      : tone === "warning"
        ? theme.status.warning
        : tone === "error"
          ? theme.status.critical
          : theme.palette.text.secondary;

  return (
    <Paper
      variant="outlined"
      sx={{
        alignItems: "flex-start",
        borderRadius: 1.5,
        display: "flex",
        flexDirection: "column",
        gap: 1,
        minHeight: (theme) => theme.appLayout.kpiMinHeight,
        p: 3,
      }}
    >
      <Typography color="text.secondary" variant="body2">{label}</Typography>
      <Typography sx={{ color: toneColor, fontWeight: 800, fontVariantNumeric: "tabular-nums" }} variant="h2">
        {value}
      </Typography>
      {subtitle && (
        <Typography color="text.secondary" variant="body2">{subtitle}</Typography>
      )}
    </Paper>
  );
}

// ── Trend Chart ──

interface TrendChartProps {
  periods: DashboardOverview["trend"]["periods"];
  sourceNames: Map<string, string>;
  thresholdValue?: number | null;
}

function TrendChart({ periods, sourceNames, thresholdValue }: TrendChartProps) {
  const theme = useTheme();
  const chartRef = useRef<HTMLDivElement>(null);
  const [renderError, setRenderError] = useState(false);
  const chartAcceptanceMetadata = useMemo(() => {
    const sourceIds = new Set<string>();
    let technicalErrorCount = 0;
    let versionBoundaryCount = 0;
    const versionLabels = new Set<string>();
    for (const period of periods) {
      for (const observation of period.observations) {
        if (observation.scopeType === "SOURCE" && observation.scopeId) {
          sourceIds.add(observation.scopeId);
        }
        if (
          observation.scopeType === "ENTERPRISE"
          && observation.scoreStatus === "NOT_CALCULATED_TECHNICAL_ERROR"
        ) {
          technicalErrorCount += 1;
        }
        if (observation.versionBoundary) {
          versionBoundaryCount += 1;
          versionLabels.add(observation.policyVersion ?? "Sürüm değişimi");
        }
      }
    }
    return {
      sourceSeriesCount: sourceIds.size,
      technicalErrorCount,
      versionBoundaryCount,
      versionLabels: Array.from(versionLabels).join(","),
    };
  }, [periods]);

  useEffect(() => {
    if (!chartRef.current) return;
    let chart: echarts.ECharts | undefined;
    let resizeObserver: ResizeObserver | undefined;

    try {
      setRenderError(false);
      chart = echarts.init(chartRef.current, undefined, { renderer: "canvas" });

      const dates: string[] = [];
      const enterpriseValues: (number | null)[] = [];
      const movingAvgValues: (number | null)[] = [];
      const sourceIds = new Set<string>();
      const errorPoints: Array<[number, number]> = [];
      const versionBoundaryIndices: number[] = [];
      const effectiveThreshold = thresholdValue ?? 70;

      for (let i = 0; i < periods.length; i++) {
        const period = periods[i];
        dates.push(new Date(period.periodStart).toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit" }));
        const enterpriseObs = period.observations.find((o) => o.scopeType === "ENTERPRISE");
        enterpriseValues.push(enterpriseObs?.scoreValue ?? null);
        movingAvgValues.push(enterpriseObs?.trend?.movingAverage ?? null);
        if (enterpriseObs?.versionBoundary) versionBoundaryIndices.push(i);
        for (const obs of period.observations) {
          if (obs.scopeType === "SOURCE" && obs.scopeId) sourceIds.add(obs.scopeId);
        }
        if (enterpriseObs?.scoreStatus === "NOT_CALCULATED_TECHNICAL_ERROR") {
          errorPoints.push([i, enterpriseObs.scoreValue ?? 0]);
        }
      }

      const series: Array<Record<string, unknown>> = [
        {
          name: "Kurumsal Skor",
          type: "line",
          data: enterpriseValues,
          connectNulls: false,
          lineStyle: { color: designTokens.color.brand.primary, width: 2 },
          itemStyle: { color: designTokens.color.brand.primary },
          symbol: "circle",
          symbolSize: 6,
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: theme.status.warning, type: "dashed", width: 1 },
            data: [
              {
                yAxis: effectiveThreshold,
                label: {
                  formatter: `Eşik: ${effectiveThreshold}`,
                  color: theme.palette.text.secondary,
                  fontSize: 11,
                },
              },
              ...versionBoundaryIndices.map((idx) => ({
                xAxis: idx,
                lineStyle: { color: theme.palette.text.disabled, type: "dashed" as const, width: 1 },
                label: {
                  formatter: () => {
                    const obs = periods[idx]?.observations.find((o) => o.scopeType === "ENTERPRISE");
                    return obs?.policyVersion ? `v: ${obs.policyVersion}` : "Sürüm değişimi";
                  },
                  color: theme.palette.text.secondary,
                  fontSize: 10,
                },
              })),
            ],
          },
          markPoint: {
            data: periods.flatMap((period, idx) => {
              const obs = period.observations.find((o) => o.scopeType === "ENTERPRISE");
              if (!obs) return [];
              const points: Array<Record<string, unknown>> = [];
              if (obs.trend?.suddenDeterioration) {
                points.push({
                  coord: [idx, obs.scoreValue ?? 0],
                  symbol: "triangle",
                  symbolSize: 14,
                  itemStyle: { color: theme.status.critical },
                  label: { show: false },
                });
              }
              if (obs.trend?.consecutiveDeteriorationCount != null && obs.trend.consecutiveDeteriorationCount >= 3) {
                points.push({
                  coord: [idx, obs.scoreValue ?? 0],
                  symbol: "circle",
                  symbolSize: 10,
                  itemStyle: { color: theme.status.warning },
                  label: { show: false },
                });
              }
              return points;
            }),
          },
        },
      ];
      for (const sourceId of sourceIds) {
        const name = sourceNames.get(sourceId) ?? sourceId;
        series.push({
          id: `source:${sourceId}`,
          name,
          type: "line",
          data: periods.map((period) => period.observations.find(
            (observation) => observation.scopeType === "SOURCE" && observation.scopeId === sourceId,
          )?.scoreValue ?? null),
          connectNulls: false,
          lineStyle: { color: theme.palette.text.secondary, width: 1, opacity: 0.5 },
          itemStyle: { color: theme.palette.text.secondary, opacity: 0.5 },
          symbol: "none",
        });
      }
      series.push({
        name: "Hareketli Ortalama",
        type: "line",
        data: movingAvgValues,
        connectNulls: false,
        lineStyle: { color: designTokens.color.brand.primary, width: 1, type: "dashed", opacity: 0.5 },
        itemStyle: { color: designTokens.color.brand.primary, opacity: 0.5 },
        symbol: "none",
      });
      series.push({
        name: "Teknik Hata",
        type: "scatter",
        data: errorPoints,
        itemStyle: { color: theme.status.technical },
        symbolSize: 10,
      });

      const option: EChartsCoreOption = {
        animation: false,
        grid: { left: 48, right: 24, top: 56, bottom: 32 },
        tooltip: {
          trigger: "axis",
          formatter: createTrendTooltipFormatter(periods, {
            critical: theme.status.critical,
            success: theme.status.success,
            muted: theme.palette.text.secondary,
            chipBackground: theme.palette.action.selected,
          }, sourceNames),
        },
        legend: { type: "scroll", top: 0, textStyle: { fontSize: 11 } },
        xAxis: {
          type: "category",
          data: dates,
          axisLabel: { color: theme.palette.text.secondary, fontSize: 11 },
          axisLine: { lineStyle: { color: theme.palette.divider } },
        },
        yAxis: {
          type: "value",
          min: 0,
          max: 100,
          axisLabel: { color: theme.palette.text.secondary, fontSize: 11 },
          splitLine: { lineStyle: { color: theme.palette.divider } },
        },
        series,
      };
      chart.setOption(option);

      resizeObserver = new ResizeObserver(() => {
        try {
          chart?.resize();
        } catch {
          setRenderError(true);
        }
      });
      resizeObserver.observe(chartRef.current);
    } catch {
      setRenderError(true);
    }
    return () => {
      resizeObserver?.disconnect();
      chart?.dispose();
    };
  }, [periods, sourceNames, theme, thresholdValue]);

  return (
    <>
      {renderError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Grafik görüntülenemedi. Verileri Tablo sekmesinden inceleyebilirsiniz.
        </Alert>
      )}
      <Box
        ref={chartRef}
        role="img"
        aria-label="Kalite trend grafiği"
        data-period-count={periods.length}
        data-source-series-count={chartAcceptanceMetadata.sourceSeriesCount}
        data-technical-error-count={chartAcceptanceMetadata.technicalErrorCount}
        data-technical-marker-color={theme.status.technical}
        data-threshold-value={thresholdValue ?? 70}
        data-version-boundary-count={chartAcceptanceMetadata.versionBoundaryCount}
        data-version-labels={chartAcceptanceMetadata.versionLabels}
        sx={(theme) => ({ display: renderError ? "none" : "block", height: theme.appLayout.chartHeight, width: "100%" })}
      />
    </>
  );
}

export function TrendTable({ periods }: TrendChartProps) {
  return (
    <TableContainer sx={(theme) => ({ maxHeight: theme.appLayout.tableMaxHeight })}>
      <Table stickyHeader size="small" aria-label="Kalite trend tablosu">
        <TableHead>
          <TableRow>
            <TableCell scope="col">Dönem</TableCell>
            <TableCell align="right" scope="col">Kurumsal Skor</TableCell>
            <TableCell scope="col">Seviye</TableCell>
            <TableCell align="right" scope="col">Değişim</TableCell>
            <TableCell scope="col">Durum</TableCell>
            <TableCell align="right" scope="col">Kaynak Sayısı</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {periods.length > 0 ? periods.map((period) => {
            const enterprise = period.observations.find((observation) => observation.scopeType === "ENTERPRISE");
            const sourceCount = period.observations.filter((observation) => observation.scopeType === "SOURCE").length;
            return (
              <TableRow key={`${period.periodStart}-${period.periodEnd}`} hover>
                <TableCell>{new Date(period.periodStart).toLocaleDateString("tr-TR")}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{formatScore(enterprise?.scoreValue ?? null)}</TableCell>
                <TableCell>{enterprise?.level ?? "—"}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{formatChange(enterprise?.change ?? null)}</TableCell>
                <TableCell>{enterprise ? statusLabel[enterprise.scoreStatus] ?? enterprise.scoreStatus : "—"}</TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{sourceCount}</TableCell>
              </TableRow>
            );
          }) : (
            <TableRow>
              <TableCell colSpan={6}>
                <Typography color="text.secondary" sx={{ py: 2, textAlign: "center" }} variant="body2">
                  Henüz trend verisi bulunmuyor.
                </Typography>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

function TrendView({ periods, sourceNames, thresholdValue }: TrendChartProps) {
  const [selectedTab, setSelectedTab] = useState(0);

  return (
    <>
      <Tabs aria-label="Trend görünümü" onChange={(_event, value: number) => setSelectedTab(value)} value={selectedTab}>
        <Tab aria-controls="trend-chart-panel" id="trend-chart-tab" label="Grafik" />
        <Tab aria-controls="trend-table-panel" id="trend-table-tab" label="Tablo" />
      </Tabs>
      <Box aria-labelledby="trend-chart-tab" hidden={selectedTab !== 0} id="trend-chart-panel" role="tabpanel" sx={{ pt: 2 }}>
        {selectedTab === 0 && (
          <TrendChart periods={periods} sourceNames={sourceNames} thresholdValue={thresholdValue} />
        )}
      </Box>
      <Box aria-labelledby="trend-table-tab" hidden={selectedTab !== 1} id="trend-table-panel" role="tabpanel" sx={{ pt: 2 }}>
        {selectedTab === 1 && <TrendTable periods={periods} sourceNames={sourceNames} />}
      </Box>
    </>
  );
}

// ── Source Scores Table ──

interface SourceTableProps {
  sources: DashboardScoreNode[];
  sourceNames: Map<string, string>;
  sparklinesBySource: Map<string, (number | null)[]>;
}

function SparklineCell({ values }: { values: (number | null)[] }) {
  const theme = useTheme();
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || values.length === 0) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const validValues = values.filter((v) => v !== null) as number[];
    if (validValues.length < 2) return;

    const min = 0;
    const max = 100;
    const stepX = w / (values.length - 1);

    ctx.beginPath();
    ctx.strokeStyle = designTokens.color.brand.primary;
    ctx.lineWidth = 1.5;
    let started = false;
    values.forEach((v, i) => {
      if (v === null) { started = false; return; }
      const x = i * stepX;
      const y = h - ((v - min) / (max - min)) * h;
      if (!started) { ctx.moveTo(x, y); started = true; } else { ctx.lineTo(x, y); }
    });
    ctx.stroke();
  }, [values, theme]);

  return (
    <canvas
      ref={canvasRef}
      aria-label="Kaynak skor sparkline grafiği"
      role="img"
      style={{ width: 80, height: 28, display: "block" }}
    />
  );
}

function SourceTable({ sources, sourceNames, sparklinesBySource }: SourceTableProps) {
  return (
    <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 1.5 }}>
      <Table size="small" aria-label="Kaynak bazlı skorlar">
        <TableHead>
          <TableRow>
            <TableCell>Kaynak</TableCell>
            <TableCell align="right">Ortalama Kalite</TableCell>
            <TableCell>Seviye</TableCell>
            <TableCell>Durum</TableCell>
            <TableCell align="right">Değişim</TableCell>
            <TableCell>Trend (7g)</TableCell>
            <TableCell>Zaman</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {sources.map((source) => {
            const displayName = sourceNames.get(source.scopeId ?? "") ?? source.scopeId ?? "—";
            return (
              <TableRow key={source.qualityScoreId} hover>
                <TableCell>
                  <Link to={`/data-sources`}>
                    {displayName}
                  </Link>
                </TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                  {formatScore(source.scoreValue)}
                </TableCell>
                <TableCell>
                  {source.level ? (
                    <Chip color={levelColor(source.level)} label={source.level} size="small" />
                  ) : "—"}
                </TableCell>
                <TableCell>
                  <Chip
                    color={source.scoreStatus === "CALCULATED" ? "success" : source.scoreStatus === "NOT_CALCULATED_TECHNICAL_ERROR" ? "error" : "default"}
                    label={statusLabel[source.scoreStatus] ?? source.scoreStatus}
                    size="small"
                  />
                </TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                  {formatChange(source.change)}
                </TableCell>
                <TableCell>
                  {(() => {
                    const sparkData = sparklinesBySource.get(source.scopeId ?? "") ?? [];
                    return sparkData.length > 1 ? <SparklineCell values={sparkData} /> : <Typography color="text.secondary" variant="body2">—</Typography>;
                  })()}
                </TableCell>
                <TableCell>
                  {new Date(source.calculatedAt).toLocaleString("tr-TR")}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

// ── Dataset Quality Table ──

interface DatasetQualityRow {
  datasetId: string;
  name: string;
  namespace: string;
  sourceName: string;
  score: ScoreListItem | null;
}

function DatasetTable({
  datasets,
  sourceNames,
  datasetScores,
  searchQuery,
  onSearchChange,
}: {
  datasets: { id: string; name: string; namespace: string; data_source_id: string }[];
  sourceNames: Map<string, string>;
  datasetScores: Map<string, ScoreListItem>;
  searchQuery: string;
  onSearchChange: (value: string) => void;
}) {
  const rows: DatasetQualityRow[] = useMemo(() => {
    return datasets.map((ds) => ({
      datasetId: ds.id,
      name: ds.name,
      namespace: ds.namespace,
      sourceName: sourceNames.get(ds.data_source_id) ?? ds.data_source_id,
      score: datasetScores.get(ds.id) ?? null,
    }));
  }, [datasets, sourceNames, datasetScores]);

  const filteredRows = useMemo(() => {
    if (!searchQuery.trim()) return rows;
    const q = searchQuery.toLocaleLowerCase("tr-TR");
    return rows.filter(
      (r) =>
        r.name.toLocaleLowerCase("tr-TR").includes(q) ||
        r.namespace.toLocaleLowerCase("tr-TR").includes(q) ||
        r.sourceName.toLocaleLowerCase("tr-TR").includes(q) ||
        r.datasetId.toLocaleLowerCase("tr-TR").includes(q),
    );
  }, [rows, searchQuery]);

  return (
    <Stack sx={{ gap: 2 }}>
      <TextField
        label="Dataset ara"
        onChange={(e) => onSearchChange(e.target.value)}
        slotProps={{ input: { startAdornment: <Search aria-hidden="true" size={16} /> } }}
        sx={{ maxWidth: 400 }}
        value={searchQuery}
      />
      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 1.5 }}>
        <Table size="small" aria-label="Dataset kalitesi">
          <TableHead>
            <TableRow>
              <TableCell>Dataset</TableCell>
              <TableCell>Kaynak</TableCell>
              <TableCell align="right">Skor</TableCell>
              <TableCell>Seviye</TableCell>
              <TableCell>Durum</TableCell>
              <TableCell>Zaman</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredRows.length > 0 ? (
              filteredRows.map((row) => (
                <TableRow key={row.datasetId} hover>
                  <TableCell>
                    <Link to={`/catalog/datasets/${row.datasetId}/trend`}>
                      {row.namespace}.{row.name}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{row.sourceName}</Typography>
                  </TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                    {row.score ? formatScore(row.score.scoreValue) : "—"}
                  </TableCell>
                  <TableCell>
                    {row.score?.level ? (
                      <Chip color={levelColor(row.score.level)} label={row.score.level} size="small" />
                    ) : "—"}
                  </TableCell>
                  <TableCell>
                    {row.score ? (
                      <Chip
                        color={row.score.scoreStatus === "CALCULATED" ? "success" : row.score.scoreStatus === "NOT_CALCULATED_TECHNICAL_ERROR" ? "error" : "default"}
                        label={statusLabel[row.score.scoreStatus] ?? row.score.scoreStatus}
                        size="small"
                      />
                    ) : (
                      <Chip color="default" label={statusLabel.NO_DATA ?? "Veri yok"} size="small" />
                    )}
                  </TableCell>
                  <TableCell>
                    {row.score ? new Date(row.score.calculatedAt).toLocaleString("tr-TR") : "—"}
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6}>
                  <Typography color="text.secondary" sx={{ py: 2, textAlign: "center" }} variant="body2">
                    {searchQuery ? "Aramayla eşleşen dataset bulunamadı." : "Henüz dataset bulunmuyor."}
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Stack>
  );
}

// ── Main Page ──

export function DashboardPage() {
  const [state, setState] = useState<DashboardState>("loading");
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [errorKind, setErrorKind] = useState<string | null>(null);
  const [sourceNames, setSourceNames] = useState<Map<string, string>>(new Map());
  const [catalogDatasets, setCatalogDatasets] = useState<{ id: string; name: string; namespace: string; data_source_id: string }[]>([]);
  const [datasetScores, setDatasetScores] = useState<Map<string, ScoreListItem>>(new Map());
  const [datasetSearch, setDatasetSearch] = useState("");
  const [trendWindow, setTrendWindow] = useState<TrendWindow>("30g");
  const [filterStartDate, setFilterStartDate] = useState("");
  const [filterEndDate, setFilterEndDate] = useState("");
  const [filterSourceId, setFilterSourceId] = useState("");

  const load = useCallback(async (signal?: AbortSignal) => {
    setState("loading");
    setErrorKind(null);
    try {
      const [dashResponse, catalogResponse, sourcesResponse, scoresResponse] = await Promise.all([
        fetchDashboardOverview({
          startDate: filterStartDate || undefined,
          endDate: filterEndDate || undefined,
          scopeType: filterSourceId ? "SOURCE" : undefined,
          scopeId: filterSourceId || undefined,
        }, signal),
        listCatalogDatasets(undefined).catch(() => null),
        fetchDataSources(signal).catch(() => null),
        fetchScores({ scopeType: "DATASET", limit: 200 }, signal).catch(() => null),
      ]);
      const mapped = overviewFromApi(dashResponse);
      setOverview(mapped);
      setState("normal");

      // Build source name lookup
      if (sourcesResponse) {
        const names = new Map<string, string>();
        for (const src of sourcesResponse.items) {
          names.set(src.data_source_id, src.name);
        }
        setSourceNames(names);
      }

      // Build flat dataset list
      if (catalogResponse) {
        const flat: { id: string; name: string; namespace: string; data_source_id: string }[] = [];
        for (const ds of catalogResponse.items) {
          flat.push({ id: ds.dataset_id, name: ds.name, namespace: ds.namespace, data_source_id: ds.data_source_id });
        }
        setCatalogDatasets(flat);
      }

      // Build dataset score lookup
      if (scoresResponse) {
        const scoreMap = new Map<string, ScoreListItem>();
        const scores = scoresFromApi(scoresResponse);
        for (const score of scores) {
          if (score.scopeId && (!scoreMap.has(score.scopeId) || new Date(score.calculatedAt) > new Date(scoreMap.get(score.scopeId)!.calculatedAt))) {
            scoreMap.set(score.scopeId, score);
          }
        }
        setDatasetScores(scoreMap);
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      if (error instanceof DashboardApiError) {
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
  }, [filterEndDate, filterSourceId, filterStartDate]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const latestEnterprise = useMemo(() => {
    if (!overview) return null;
    for (let i = overview.trend.periods.length - 1; i >= 0; i--) {
      const period = overview.trend.periods[i];
      const enterprise = period.observations.find((o) => o.scopeType === "ENTERPRISE");
      if (enterprise) return enterprise;
    }
    return null;
  }, [overview]);

  const latestSources = useMemo(() => {
    if (!overview) return [];
    const sourceMap = new Map<string, DashboardScoreNode>();
    for (const period of overview.trend.periods) {
      for (const obs of period.observations) {
        if (obs.scopeType === "SOURCE" && obs.scopeId) {
          const existing = sourceMap.get(obs.scopeId);
          if (!existing || new Date(obs.calculatedAt) > new Date(existing.calculatedAt)) {
            sourceMap.set(obs.scopeId, obs);
          }
        }
      }
    }
    return Array.from(sourceMap.values()).sort((a, b) => (a.scopeId ?? "").localeCompare(b.scopeId ?? ""));
  }, [overview]);

  const sparklinesBySource = useMemo(() => {
    const map = new Map<string, (number | null)[]>();
    if (!overview) return map;
    // Collect last 7 periods of source scores
    const periods = overview.trend.periods.slice(-7);
    for (const source of latestSources) {
      const values: (number | null)[] = [];
      for (const period of periods) {
        const obs = period.observations.find(
          (o) => o.scopeType === "SOURCE" && o.scopeId === source.scopeId,
        );
        values.push(obs?.scoreValue ?? null);
      }
      map.set(source.scopeId ?? "", values);
    }
    return map;
  }, [overview, latestSources]);

  const visibleTrendPeriods = useMemo(
    () => overview?.trend.periods.slice(-trendWindowDays[trendWindow]) ?? [],
    [overview, trendWindow],
  );

  const hasActiveFilters = Boolean(filterStartDate || filterEndDate || filterSourceId);
  const activeFilterSummary = useMemo(() => {
    const filters: string[] = [];
    if (filterStartDate) filters.push(`Başlangıç ${filterStartDate}`);
    if (filterEndDate) filters.push(`Bitiş ${filterEndDate}`);
    if (filterSourceId) filters.push(`Kaynak ${sourceNames.get(filterSourceId) ?? filterSourceId}`);
    return filters.join(" · ");
  }, [filterEndDate, filterSourceId, filterStartDate, sourceNames]);

  const content = useMemo(() => {
    if (state === "loading") {
      return (
        <Box sx={{ alignItems: "center", display: "flex", justifyContent: "center", py: 10 }}>
          <CircularProgress aria-label="Dashboard yükleniyor" />
        </Box>
      );
    }
    if (state === "unauthorized") {
      return <Alert severity="warning">Bu sayfayı görüntüleme yetkiniz yok.</Alert>;
    }
    if (state === "error") {
      return <Alert severity="error">Dashboard yüklenemedi ({errorKind}).</Alert>;
    }
    if (!overview) {
      return <Alert severity="info">Henüz dashboard verisi bulunmuyor.</Alert>;
    }

    const qualification = overview.operationalIndicators.measurementQualification;
    const techErrors = overview.operationalIndicators.technicalErrors;

    return (
      <Stack sx={{ gap: 4 }}>
        {/* KPI Cards */}
        <Box
          sx={{
            display: "grid",
            gap: 3,
            gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", md: "1fr 1fr 1fr 1fr" },
          }}
        >
          <KpiCard
            label="Kalite Skoru"
            value={formatScore(latestEnterprise?.scoreValue ?? null)}
            subtitle={latestEnterprise ? statusLabel[latestEnterprise.scoreStatus] ?? latestEnterprise.scoreStatus : "Veri yok"}
            tone={latestEnterprise?.level === "GOOD" ? "success" : latestEnterprise?.level === "ACCEPTABLE" ? "warning" : latestEnterprise?.level ? "error" : "default"}
          />
          <KpiCard
            label="Ölçüm Yeterliliği"
            value={qualificationLabel[qualification.status] ?? qualification.status}
            subtitle={`${qualification.evaluatedScopeCount} kapsam değerlendirildi`}
            tone={qualification.status === "VALIDATION_REQUIRED" ? "warning" : qualification.status === "TECHNICAL_FAILURE" ? "error" : "default"}
          />
          <KpiCard
            label="Teknik Hatalar"
            value={String(techErrors.observationCount)}
            subtitle={`${techErrors.affectedSourceCount} kaynak etkilenen`}
            tone={techErrors.observationCount > 0 ? "technical" : "success"}
          />
          <KpiCard
            label="Kaynak Sayısı"
            value={String(latestSources.length)}
            subtitle="İzlenen veri kaynağı"
          />
        </Box>

        {/* Trend Chart */}
        {overview.trend.hasData ? (
          <Paper component="section" variant="outlined" sx={{ borderRadius: 1.5, overflow: "hidden", p: 4 }}>
            <Box
              sx={{
                alignItems: { xs: "flex-start", sm: "center" },
                display: "flex",
                flexDirection: { xs: "column", sm: "row" },
                gap: 2,
                justifyContent: "space-between",
                mb: 2,
              }}
            >
              <Typography component="h2" variant="h3">
                Kalite Trendi
              </Typography>
              <ToggleButtonGroup
                aria-label="Trend dönemi"
                exclusive
                onChange={(_event, value: TrendWindow | null) => {
                  if (value !== null) setTrendWindow(value);
                }}
                size="small"
                value={trendWindow}
              >
                {(Object.keys(trendWindowDays) as TrendWindow[]).map((window) => (
                  <ToggleButton
                    aria-label={trendWindowLabels[window]}
                    key={window}
                    sx={{ minHeight: 44, minWidth: 52 }}
                    value={window}
                  >
                    {window}
                  </ToggleButton>
                ))}
              </ToggleButtonGroup>
            </Box>
            <TrendView
              periods={visibleTrendPeriods}
              sourceNames={sourceNames}
              thresholdValue={overview.trend.thresholdValue}
            />
          </Paper>
        ) : (
          <Alert severity="info">Henüz trend verisi bulunmuyor. Diğer dashboard verilerini aşağıda inceleyebilirsiniz.</Alert>
        )}

        {/* Source Scores */}
        {latestSources.length > 0 && (
          <Box component="section">
            <Typography component="h2" sx={{ mb: 2 }} variant="h3">
              Kaynak Bazlı Skorlar
            </Typography>
            <SourceTable sources={latestSources} sourceNames={sourceNames} sparklinesBySource={sparklinesBySource} />
          </Box>
        )}

        {/* Dataset Quality */}
        {catalogDatasets.length > 0 && (
          <Box component="section">
            <Typography component="h2" sx={{ mb: 2 }} variant="h3">
              Dataset Kalitesi
            </Typography>
            <DatasetTable
              datasets={catalogDatasets}
              sourceNames={sourceNames}
              datasetScores={datasetScores}
              searchQuery={datasetSearch}
              onSearchChange={setDatasetSearch}
            />
          </Box>
        )}
      </Stack>
    );
  }, [state, overview, latestEnterprise, latestSources, errorKind, sourceNames, sparklinesBySource, catalogDatasets, datasetScores, datasetSearch, trendWindow, visibleTrendPeriods]);

  return (
    <AppShell currentPage="Genel Bakış">
      <Stack sx={{ gap: 4, p: { md: 4, lg: 6 } }}>
        <Box sx={{ alignItems: "flex-start", display: "flex", flexWrap: "wrap", gap: 2, justifyContent: "space-between" }}>
          <Stack sx={{ gap: 0.5 }}>
            <Typography variant="h1">Genel Bakış</Typography>
            <Typography color="text.secondary" variant="body2">
              Aktif dönem: {trendWindowLabels[trendWindow]}
            </Typography>
            {hasActiveFilters && (
              <Typography color="text.secondary" variant="body2">
                Aktif filtreler: {activeFilterSummary}
              </Typography>
            )}
          </Stack>
          {overview && (
            <Typography color="text.secondary" variant="body2">
              {new Date(overview.trend.asOf).toLocaleString("tr-TR")}
            </Typography>
          )}
        </Box>
        <Paper
          aria-label="Dashboard filtreleri"
          component="section"
          variant="outlined"
          sx={{ borderRadius: 1.5, p: 2 }}
        >
          <Stack
            direction={{ xs: "column", md: "row" }}
            sx={{ alignItems: { md: "center" }, gap: 2 }}
          >
            <TextField
              label="Başlangıç tarihi"
              onChange={(event) => setFilterStartDate(event.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              type="date"
              value={filterStartDate}
            />
            <TextField
              label="Bitiş tarihi"
              onChange={(event) => setFilterEndDate(event.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              type="date"
              value={filterEndDate}
            />
            <FormControl sx={{ minWidth: 240 }}>
              <InputLabel id="dashboard-source-filter-label">Kaynak</InputLabel>
              <Select
                label="Kaynak"
                labelId="dashboard-source-filter-label"
                onChange={(event) => setFilterSourceId(event.target.value)}
                value={filterSourceId}
              >
                <MenuItem value="">Tüm yetkili kaynaklar</MenuItem>
                {Array.from(sourceNames.entries())
                  .sort((left, right) => left[1].localeCompare(right[1], "tr"))
                  .map(([sourceId, sourceName]) => (
                    <MenuItem key={sourceId} value={sourceId}>{sourceName}</MenuItem>
                  ))}
              </Select>
            </FormControl>
            <Button
              disabled={!hasActiveFilters}
              onClick={() => {
                setFilterStartDate("");
                setFilterEndDate("");
                setFilterSourceId("");
              }}
              variant="outlined"
            >
              Filtreleri Temizle
            </Button>
          </Stack>
        </Paper>
        {content}
      </Stack>
    </AppShell>
  );
}
