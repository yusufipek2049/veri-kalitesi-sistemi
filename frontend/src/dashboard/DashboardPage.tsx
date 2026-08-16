import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsCoreOption } from "echarts/core";
import { Info, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { designTokens } from "../theme/tokens";
import { listCatalogDatasets } from "../catalog/api";
import { fetchDataSources } from "../dataSources/api";
import { fetchScoreDetail, fetchScores } from "../scores/api";
import {
  scoreDetailFromApi,
  scoresFromApi,
  type ScoreDetail,
  type ScoreListItem,
} from "../scores/model";
import { DashboardApiError, fetchDashboardOverview } from "./api";
import { overviewFromApi, type DashboardOverview, type DashboardScoreNode, type DashboardState } from "./model";

echarts.use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

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

function dayKey(value: string): string {
  return value.slice(0, 10);
}

function formatDayLabel(value: string): string {
  return new Date(value).toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit" });
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

// ── Dataset Trend (DB'deki datasetler ve dataset bazlı skorlarla beslenir) ──

interface DatasetTrendRow {
  datasetId: string;
  displayName: string;
  sourceName: string;
  latest: ScoreListItem | null;
  points: Array<{ day: string; value: number }>;
}

interface TrendPoint {
  day: string;
  value: number;
}

function DatasetTrendChart({ averagePoints, rows }: { averagePoints: TrendPoint[]; rows: DatasetTrendRow[] }) {
  const theme = useTheme();
  const chartRef = useRef<HTMLDivElement>(null);
  const [renderError, setRenderError] = useState(false);
  const dayCount = useMemo(() => {
    const days = new Set<string>();
    for (const point of averagePoints) days.add(point.day);
    for (const row of rows) {
      for (const point of row.points) days.add(point.day);
    }
    return days.size;
  }, [averagePoints, rows]);

  useEffect(() => {
    if (!chartRef.current) return;
    let chart: echarts.ECharts | undefined;
    let resizeObserver: ResizeObserver | undefined;

    try {
      setRenderError(false);
      chart = echarts.init(chartRef.current, undefined, { renderer: "canvas" });

      const days = new Set<string>();
      for (const point of averagePoints) days.add(point.day);
      for (const row of rows) {
        for (const point of row.points) days.add(point.day);
      }
      const sortedDays = Array.from(days).sort();
      const palette = [
        designTokens.color.brand.primary,
        theme.status.success,
        theme.status.warning,
        theme.status.critical,
        theme.status.technical,
        theme.palette.text.secondary,
      ];
      const averagesByDay = new Map(averagePoints.map((point) => [point.day, point.value]));
      const series: Array<Record<string, unknown>> = [{
        name: "Genel Ortalama",
        type: "line",
        data: sortedDays.map((day) => averagesByDay.get(day) ?? null),
        connectNulls: false,
        lineStyle: { color: designTokens.color.brand.primary, width: 4 },
        itemStyle: { color: designTokens.color.brand.primary },
        symbol: "diamond",
        symbolSize: 7,
        z: 10,
      }, ...rows.map((row, index) => {
        const valuesByDay = new Map(row.points.map((point) => [point.day, point.value]));
        const color = palette[(index + 1) % palette.length];
        return {
          name: row.displayName,
          type: "line",
          data: sortedDays.map((day) => valuesByDay.get(day) ?? null),
          connectNulls: false,
          lineStyle: { color, width: 2 },
          itemStyle: { color },
          symbol: "circle",
          symbolSize: 5,
        };
      })];

      const option: EChartsCoreOption = {
        animation: false,
        grid: { left: 48, right: 24, top: 56, bottom: 32 },
        tooltip: { trigger: "axis" },
        legend: { type: "scroll", top: 0, textStyle: { fontSize: 11 } },
        xAxis: {
          type: "category",
          data: sortedDays.map(formatDayLabel),
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
  }, [averagePoints, rows, theme]);

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
        data-day-count={dayCount}
        data-dataset-series-count={rows.length}
        data-has-average-series={averagePoints.length > 0}
        sx={(theme) => ({ display: renderError ? "none" : "block", height: theme.appLayout.chartHeight, width: "100%" })}
      />
    </>
  );
}

export function DatasetTrendTable({
  rows,
  onDetail,
}: {
  rows: DatasetTrendRow[];
  onDetail: (qualityScoreId: string) => void;
}) {
  return (
    <TableContainer sx={(theme) => ({ maxHeight: theme.appLayout.tableMaxHeight })}>
      <Table stickyHeader size="small" aria-label="Kalite trend tablosu">
        <TableHead>
          <TableRow>
            <TableCell scope="col">Dataset</TableCell>
            <TableCell scope="col">Kaynak</TableCell>
            <TableCell align="right" scope="col">Son Skor</TableCell>
            <TableCell scope="col">Seviye</TableCell>
            <TableCell scope="col">Durum</TableCell>
            <TableCell scope="col">Zaman</TableCell>
            <TableCell align="right" scope="col">Detay</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.length > 0 ? rows.map((row) => (
            <TableRow key={row.datasetId} hover>
              <TableCell>
                <Link to={`/catalog/datasets/${row.datasetId}/trend`}>
                  {row.displayName}
                </Link>
              </TableCell>
              <TableCell>
                <Typography variant="body2">{row.sourceName}</Typography>
              </TableCell>
              <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                {formatScore(row.latest?.scoreValue ?? null)}
              </TableCell>
              <TableCell>
                {row.latest?.level ? (
                  <Chip color={levelColor(row.latest.level)} label={row.latest.level} size="small" />
                ) : "—"}
              </TableCell>
              <TableCell>
                {row.latest ? statusLabel[row.latest.scoreStatus] ?? row.latest.scoreStatus : "—"}
              </TableCell>
              <TableCell>
                {row.latest ? new Date(row.latest.calculatedAt).toLocaleString("tr-TR") : "—"}
              </TableCell>
              <TableCell align="right">
                <Button
                  disabled={!row.latest}
                  onClick={() => row.latest && onDetail(row.latest.id)}
                  size="small"
                  startIcon={<Info aria-hidden="true" size={14} />}
                  variant="outlined"
                >
                  Detaylı Bilgi
                </Button>
              </TableCell>
            </TableRow>
          )) : (
            <TableRow>
              <TableCell colSpan={7}>
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

function DatasetTrendView({
  averagePoints,
  rows,
  onDetail,
}: {
  averagePoints: TrendPoint[];
  rows: DatasetTrendRow[];
  onDetail: (qualityScoreId: string) => void;
}) {
  const [selectedTab, setSelectedTab] = useState(0);

  return (
    <>
      <Tabs aria-label="Trend görünümü" onChange={(_event, value: number) => setSelectedTab(value)} value={selectedTab}>
        <Tab aria-controls="trend-chart-panel" id="trend-chart-tab" label="Grafik" />
        <Tab aria-controls="trend-table-panel" id="trend-table-tab" label="Tablo" />
      </Tabs>
      <Box aria-labelledby="trend-chart-tab" hidden={selectedTab !== 0} id="trend-chart-panel" role="tabpanel" sx={{ pt: 2 }}>
        {selectedTab === 0 && <DatasetTrendChart averagePoints={averagePoints} rows={rows} />}
      </Box>
      <Box aria-labelledby="trend-table-tab" hidden={selectedTab !== 1} id="trend-table-panel" role="tabpanel" sx={{ pt: 2 }}>
        {selectedTab === 1 && <DatasetTrendTable rows={rows} onDetail={onDetail} />}
      </Box>
    </>
  );
}

// ── Score Detail Dialog (Detaylı Bilgi) ──

function formatDetailValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function ScoreDetailDialog({ scoreId, onClose }: { scoreId: string | null; onClose: () => void }) {
  const [detail, setDetail] = useState<ScoreDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!scoreId) return;
    const controller = new AbortController();
    setLoading(true);
    setError(false);
    setDetail(null);
    fetchScoreDetail(scoreId, controller.signal)
      .then((response) => setDetail(scoreDetailFromApi(response)))
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [scoreId]);

  return (
    <Dialog fullWidth maxWidth="md" onClose={onClose} open={scoreId !== null}>
      <DialogTitle>Skorlama Detaylı Bilgi</DialogTitle>
      <DialogContent sx={{ pt: 1 }}>
        {loading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
            <CircularProgress aria-label="Skor detayı yükleniyor" />
          </Box>
        )}
        {!loading && error && <Alert severity="error">Skor detayı yüklenemedi.</Alert>}
        {!loading && !error && detail && (
          <Stack sx={{ gap: 3 }}>
            <Box sx={{ alignItems: "center", display: "flex", flexWrap: "wrap", gap: 1 }}>
              <Typography sx={{ fontWeight: 800, fontVariantNumeric: "tabular-nums" }} variant="h2">
                {formatScore(detail.item.scoreValue)}
              </Typography>
              {detail.item.level && (
                <Chip color={levelColor(detail.item.level)} label={detail.item.level} size="small" />
              )}
              <Chip
                color={detail.item.scoreStatus === "CALCULATED" ? "success" : "default"}
                label={statusLabel[detail.item.scoreStatus] ?? detail.item.scoreStatus}
                size="small"
                variant="outlined"
              />
              <Typography color="text.secondary" variant="body2">
                {new Date(detail.item.calculatedAt).toLocaleString("tr-TR")}
              </Typography>
            </Box>

            <Box>
              <Typography sx={{ fontWeight: 700, mb: 1 }} variant="subtitle1">
                Skorlama Parametreleri
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Parametre</TableCell>
                    <TableCell>Değer</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <TableRow>
                    <TableCell>Policy sürümü</TableCell>
                    <TableCell>{detail.publication?.policyVersion ?? detail.item.policyVersion ?? "—"}</TableCell>
                  </TableRow>
                  {detail.publication && (
                    <TableRow>
                      <TableCell>Yayın durumu</TableCell>
                      <TableCell>{detail.publication.status} · {detail.publication.period}</TableCell>
                    </TableRow>
                  )}
                  {detail.calculationDetails && Object.entries(detail.calculationDetails).map(([key, value]) => (
                    <TableRow key={key}>
                      <TableCell>{key}</TableCell>
                      <TableCell sx={{ wordBreak: "break-all" }}>{formatDetailValue(value)}</TableCell>
                    </TableRow>
                  ))}
                  {detail.contributionGraph && (
                    <>
                      <TableRow>
                        <TableCell>Skor modeli sürümü</TableCell>
                        <TableCell>{detail.contributionGraph.versions.score_model_version ?? "—"}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Eşik sürümü</TableCell>
                        <TableCell>{detail.contributionGraph.versions.threshold_version ?? "—"}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Kullanım kararı</TableCell>
                        <TableCell>{detail.contributionGraph.usage_decision}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Ölçüm yeterliliği</TableCell>
                        <TableCell>{detail.contributionGraph.measurement_qualification}</TableCell>
                      </TableRow>
                    </>
                  )}
                </TableBody>
              </Table>
            </Box>

            {detail.contributionGraph && detail.contributionGraph.components.length > 0 && (
              <Box>
                <Typography sx={{ fontWeight: 700, mb: 1 }} variant="subtitle1">
                  Kural Katkıları
                </Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Bileşen</TableCell>
                      <TableCell>Tip</TableCell>
                      <TableCell align="right">Ağırlık</TableCell>
                      <TableCell align="right">Skor</TableCell>
                      <TableCell align="right">Katkı</TableCell>
                      <TableCell>Durum</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {detail.contributionGraph.components.map((component, index) => (
                      <TableRow key={`${component.component_ref}-${index}`}>
                        <TableCell sx={{ wordBreak: "break-all" }}>{component.component_ref}</TableCell>
                        <TableCell>{component.component_type}</TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                          {component.weight ?? "—"}
                        </TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                          {component.score ?? "—"}
                        </TableCell>
                        <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                          {component.contribution ?? "—"}
                        </TableCell>
                        <TableCell>
                          {component.included ? (
                            <Chip color="success" label="Dahil" size="small" />
                          ) : (
                            <Chip label={component.exclusion_reason ?? "Hariç"} size="small" variant="outlined" />
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            )}
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Kapat</Button>
      </DialogActions>
    </Dialog>
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

// ── Main Page ──

export function DashboardPage() {
  const [state, setState] = useState<DashboardState>("loading");
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [errorKind, setErrorKind] = useState<string | null>(null);
  const [sourceNames, setSourceNames] = useState<Map<string, string>>(new Map());
  const [catalogDatasets, setCatalogDatasets] = useState<{ id: string; name: string; namespace: string; data_source_id: string }[]>([]);
  const [datasetHistory, setDatasetHistory] = useState<Map<string, ScoreListItem[]>>(new Map());
  const [datasetScores, setDatasetScores] = useState<Map<string, ScoreListItem>>(new Map());
  const [datasetSearch, setDatasetSearch] = useState("");
  const [trendWindow, setTrendWindow] = useState<TrendWindow>("30g");
  const [detailScoreId, setDetailScoreId] = useState<string | null>(null);
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

      // Build dataset score history (DB'deki DATASET kapsamlı skorlar)
      if (scoresResponse) {
        const scores = scoresFromApi(scoresResponse);
        const history = new Map<string, ScoreListItem[]>();
        for (const score of scores) {
          if (!score.scopeId) continue;
          const list = history.get(score.scopeId) ?? [];
          list.push(score);
          history.set(score.scopeId, list);
        }
        for (const list of history.values()) {
          list.sort((a, b) => new Date(a.calculatedAt).getTime() - new Date(b.calculatedAt).getTime());
        }
        setDatasetHistory(history);
        const latest = new Map<string, ScoreListItem>();
        for (const [scopeId, list] of history) {
          const newest = list[list.length - 1];
          if (newest) latest.set(scopeId, newest);
        }
        setDatasetScores(latest);
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

  // Genel ortalama sabit referanstır; dataset serileri aramayla bu referansın yanına eklenir.
  const averageTrendPoints = useMemo<TrendPoint[]>(() => {
    const cutoff = Date.now() - trendWindowDays[trendWindow] * 86_400_000;
    const valuesByDay = new Map<string, number[]>();
    for (const history of datasetHistory.values()) {
      const latestScoreByDay = new Map<string, ScoreListItem>();
      for (const score of history) {
        if (new Date(score.calculatedAt).getTime() < cutoff) continue;
        latestScoreByDay.set(dayKey(score.calculatedAt), score);
      }
      for (const [day, score] of latestScoreByDay) {
        if (score.scoreValue === null) continue;
        const values = valuesByDay.get(day) ?? [];
        values.push(score.scoreValue);
        valuesByDay.set(day, values);
      }
    }
    return Array.from(valuesByDay.entries())
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([day, values]) => ({
        day,
        value: values.reduce((total, value) => total + value, 0) / values.length,
      }));
  }, [datasetHistory, trendWindow]);

  // Datasetler yalnızca arama girildiğinde görüntülenir.
  const trendRows = useMemo<DatasetTrendRow[]>(() => {
    const query = datasetSearch.trim().toLocaleLowerCase("tr-TR");
    if (!query) return [];
    const cutoff = Date.now() - trendWindowDays[trendWindow] * 86_400_000;
    const rows: DatasetTrendRow[] = [];
    for (const ds of catalogDatasets) {
      const sourceName = sourceNames.get(ds.data_source_id) ?? ds.data_source_id;
      const displayName = `${ds.namespace}.${ds.name}`;
      const haystack = `${ds.name} ${ds.namespace} ${sourceName} ${ds.id}`.toLocaleLowerCase("tr-TR");
      if (!haystack.includes(query)) continue;
      const history = datasetHistory.get(ds.id) ?? [];
      const byDay = new Map<string, ScoreListItem>();
      for (const score of history) {
        if (new Date(score.calculatedAt).getTime() < cutoff) continue;
        byDay.set(dayKey(score.calculatedAt), score);
      }
      const points = Array.from(byDay.entries())
        .sort(([left], [right]) => left.localeCompare(right))
        .flatMap(([day, score]) => score.scoreValue === null ? [] : [{ day, value: score.scoreValue }]);
      rows.push({
        datasetId: ds.id,
        displayName,
        sourceName,
        latest: datasetScores.get(ds.id) ?? null,
        points,
      });
    }
    return rows.sort((a, b) => a.displayName.localeCompare(b.displayName, "tr"));
  }, [catalogDatasets, datasetHistory, datasetScores, datasetSearch, sourceNames, trendWindow]);

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

        {/* Kalite Trendi — dataset bazlı, DB'deki DATASET kapsamlı skorlarla beslenir */}
        <Paper component="section" variant="outlined" sx={{ borderRadius: 1.5, overflow: "hidden", p: 4 }}>
          <Box
            sx={{
              alignItems: { xs: "flex-start", sm: "center" },
              display: "flex",
              flexDirection: { xs: "column", sm: "row" },
              flexWrap: "wrap",
              gap: 2,
              justifyContent: "space-between",
              mb: 2,
            }}
          >
            <Typography component="h2" variant="h3">
              Kalite Trendi
            </Typography>
            <Box sx={{ alignItems: "center", display: "flex", flexWrap: "wrap", gap: 2 }}>
              <TextField
                label="Dataset ara"
                onChange={(e) => setDatasetSearch(e.target.value)}
                size="small"
                slotProps={{ input: { startAdornment: <Search aria-hidden="true" size={16} /> } }}
                sx={{ minWidth: 240 }}
                value={datasetSearch}
              />
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
          </Box>
          <Typography color="text.secondary" sx={{ mb: 1 }} variant="body2">
            Genel ortalama sabit referans olarak gösterilir. Dataset arayarak trendi ayrıntılandırabilirsiniz.
          </Typography>
          {datasetSearch.trim() && trendRows.length === 0 && (
            <Alert severity="info">
              {averageTrendPoints.length > 0
                ? "Aramayla eşleşen dataset bulunamadı; genel ortalama gösteriliyor."
                : "Aramayla eşleşen dataset bulunamadı."}
            </Alert>
          )}
          {averageTrendPoints.length > 0 ? (
            <DatasetTrendView
              averagePoints={averageTrendPoints}
              rows={trendRows}
              onDetail={setDetailScoreId}
            />
          ) : (
            <Alert severity="info" sx={{ mt: 2 }}>
              Seçili dönemde ortalama kalite trendi için skor verisi bulunmuyor.
            </Alert>
          )}
        </Paper>

        {/* Source Scores */}
        {latestSources.length > 0 && (
          <Box component="section">
            <Typography component="h2" sx={{ mb: 2 }} variant="h3">
              Kaynak Bazlı Skorlar
            </Typography>
            <SourceTable sources={latestSources} sourceNames={sourceNames} sparklinesBySource={sparklinesBySource} />
          </Box>
        )}
      </Stack>
    );
  }, [state, overview, latestEnterprise, latestSources, errorKind, sourceNames, sparklinesBySource, averageTrendPoints, trendRows, datasetSearch, trendWindow]);

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
      <ScoreDetailDialog onClose={() => setDetailScoreId(null)} scoreId={detailScoreId} />
    </AppShell>
  );
}
