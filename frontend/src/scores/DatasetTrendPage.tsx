import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Box,
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
  Typography,
  useTheme,
} from "@mui/material";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsCoreOption } from "echarts/core";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button } from "@mui/material";
import { AppShell } from "../components/AppShell";
import { designTokens } from "../theme/tokens";
import { fetchDatasetScores, fetchScoreTrend, ScoreApiError } from "./api";
import {
  scoresFromApi,
  trendFromApi,
  type ScoreListItem,
  type ScoreTrendData,
  type TrendGranularity,
} from "./model";
import { getCatalogDataset } from "../catalog/api";
import type { CatalogDatasetDetailApiResponse } from "../catalog/model";

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

type PageState = "loading" | "normal" | "empty" | "error" | "unauthorized";

const levelColor = (level: string | null): "success" | "warning" | "error" | "default" => {
  switch (level) {
    case "GOOD": return "success";
    case "ACCEPTABLE": return "warning";
    case "RISKY":
    case "CRITICAL": return "error";
    default: return "default";
  }
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

// ── Trend Chart ──

interface TrendChartProps {
  trend: ScoreTrendData;
}

function TrendChart({ trend }: TrendChartProps) {
  const theme = useTheme();
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current || trend.points.length === 0) return;
    const chart = echarts.init(chartRef.current, undefined, { renderer: "canvas" });

    const dates = trend.points.map((p) =>
      new Date(p.timestamp).toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit" }),
    );
    const values = trend.points.map((p) => p.scoreValue);

    const option: EChartsCoreOption = {
      animation: false,
      grid: { left: 48, right: 24, top: 24, bottom: 32 },
      tooltip: {
        trigger: "axis",
        formatter: (params: unknown) => {
          const items = params as Array<{ dataIndex: number; value: number | null }>;
          if (!Array.isArray(items) || items.length === 0) return "";
          const idx = items[0].dataIndex;
          const val = items[0].value;
          const point = trend.points[idx];
          const level = point?.level ?? "—";
          return `${dates[idx]}<br/>Skor: ${val !== null ? val.toFixed(1) : "—"}<br/>Seviye: ${level}`;
        },
      },
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
      series: [
        {
          type: "line",
          data: values,
          connectNulls: false,
          lineStyle: { color: designTokens.color.brand.primary, width: 2 },
          itemStyle: { color: designTokens.color.brand.primary },
          symbol: "circle",
          symbolSize: 6,
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: theme.status.warning, type: "dashed", width: 1 },
            data: [{ yAxis: 70, label: { formatter: "Eşik: 70", color: theme.palette.text.secondary, fontSize: 11 } }],
          },
        },
      ],
    };
    chart.setOption(option);

    const resizeObserver = new ResizeObserver(() => chart.resize());
    resizeObserver.observe(chartRef.current);
    return () => {
      resizeObserver.disconnect();
      chart.dispose();
    };
  }, [trend, theme]);

  return (
    <Box
      ref={chartRef}
      role="img"
      aria-label="Dataset skor trend grafiği"
      sx={(theme) => ({ height: theme.appLayout.chartHeight, width: "100%" })}
    />
  );
}

// ── Main Page ──

export function DatasetTrendPage() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const [state, setState] = useState<PageState>("loading");
  const [trend, setTrend] = useState<ScoreTrendData | null>(null);
  const [scores, setScores] = useState<ScoreListItem[]>([]);
  const [datasetName, setDatasetName] = useState<string>();
  const [granularity, setGranularity] = useState<TrendGranularity>("day");
  const [errorKind, setErrorKind] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal, gran?: TrendGranularity) => {
    if (!datasetId) return;
    setState("loading");
    setErrorKind(null);
    try {
      const [trendResponse, scoresResponse, datasetResponse] = await Promise.all([
        fetchScoreTrend(
          { scopeType: "DATASET", scopeId: datasetId, granularity: gran ?? granularity },
          signal,
        ),
        fetchDatasetScores(datasetId, 200, signal).catch(() => null),
        getCatalogDataset(datasetId).catch(() => null),
      ]);
      const mappedTrend = trendFromApi(trendResponse);
      setTrend(mappedTrend);

      if (scoresResponse) {
        setScores(scoresFromApi(scoresResponse));
      }

      if (datasetResponse) {
        const detail = datasetResponse as CatalogDatasetDetailApiResponse;
        setDatasetName(`${detail.dataset.namespace}.${detail.dataset.name}`);
      }

      setState(mappedTrend.points.length > 0 || scores.length > 0 ? "normal" : "empty");
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      if (error instanceof ScoreApiError) {
        if (error.kind === "unauthorized") {
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
  }, [datasetId, granularity, scores.length]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const handleGranularityChange = useCallback((value: TrendGranularity) => {
    setGranularity(value);
    void load(undefined, value);
  }, [load]);

  const content = useMemo(() => {
    if (state === "loading") {
      return (
        <Box sx={{ alignItems: "center", display: "flex", justifyContent: "center", py: 10 }}>
          <CircularProgress aria-label="Trend yükleniyor" />
        </Box>
      );
    }
    if (state === "unauthorized") {
      return <Alert severity="warning">Bu sayfayı görüntüleme yetkiniz yok.</Alert>;
    }
    if (state === "error") {
      return <Alert severity="error">Trend yüklenemedi ({errorKind}).</Alert>;
    }
    if (state === "empty" || (!trend && scores.length === 0)) {
      return <Alert severity="info">Bu dataset için henüz skor verisi bulunmuyor.</Alert>;
    }

    return (
      <Stack sx={{ gap: 4 }}>
        {/* Trend Chart */}
        {trend && trend.points.length > 0 && (
          <Paper component="section" variant="outlined" sx={{ borderRadius: 1.5, overflow: "hidden", p: 4 }}>
            <Box sx={{ alignItems: "center", display: "flex", justifyContent: "space-between", mb: 2 }}>
              <Typography component="h2" variant="h3">
                Skor Trendi
              </Typography>
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel id="granularity-label">Granülerlik</InputLabel>
                <Select
                  labelId="granularity-label"
                  label="Granülerlik"
                  value={granularity}
                  onChange={(e) => handleGranularityChange(e.target.value as TrendGranularity)}
                >
                  <MenuItem value="day">Gün</MenuItem>
                  <MenuItem value="week">Hafta</MenuItem>
                  <MenuItem value="month">Ay</MenuItem>
                </Select>
              </FormControl>
            </Box>
            <TrendChart trend={trend} />
          </Paper>
        )}

        {/* Score History Table */}
        {scores.length > 0 && (
          <Paper variant="outlined" sx={{ borderRadius: 1.5, overflow: "hidden" }}>
            <Box
              sx={{
                alignItems: "center",
                borderBottom: 1,
                borderColor: "divider",
                display: "flex",
                justifyContent: "space-between",
                px: 4,
                py: 3,
              }}
            >
              <Typography component="h2" variant="h3">
                Skor Geçmişi
              </Typography>
              <Typography color="text.secondary" variant="body2">
                {scores.length} kayıt
              </Typography>
            </Box>
            <TableContainer>
              <Table size="small" aria-label="Dataset skor geçmişi">
                <TableHead>
                  <TableRow>
                    <TableCell>Tarih</TableCell>
                    <TableCell align="right">Skor</TableCell>
                    <TableCell>Seviye</TableCell>
                    <TableCell align="right">Değişim</TableCell>
                    <TableCell>Durum</TableCell>
                    <TableCell>Execution</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {scores.map((score) => (
                    <TableRow key={score.id} hover>
                      <TableCell>
                        {new Date(score.calculatedAt).toLocaleString("tr-TR")}
                      </TableCell>
                      <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                        {formatScore(score.scoreValue)}
                      </TableCell>
                      <TableCell>
                        {score.level ? (
                          <Chip color={levelColor(score.level)} label={score.level} size="small" />
                        ) : "—"}
                      </TableCell>
                      <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                        {/* Change is not directly available on list items; show dash */}
                        —
                      </TableCell>
                      <TableCell>
                        <Chip
                          color={score.scoreStatus === "CALCULATED" ? "success" : score.scoreStatus === "NOT_CALCULATED_TECHNICAL_ERROR" ? "error" : "default"}
                          label={score.scoreStatus}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Link to={`/executions`}>
                          {score.executionId.slice(0, 8)}…
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        )}
      </Stack>
    );
  }, [state, trend, scores, granularity, errorKind, handleGranularityChange]);

  return (
    <AppShell currentPage="Katalog">
      <Stack sx={{ gap: 4, p: { md: 4, lg: 6 } }}>
        <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
          <Button
            component={Link}
            to={datasetId ? `/catalog/datasets/${datasetId}` : "/catalog"}
            startIcon={<ArrowLeft aria-hidden="true" size={16} />}
            variant="text"
          >
            {datasetName ?? "Dataset"}
          </Button>
        </Box>
        <Box sx={{ alignItems: "flex-start", display: "flex", justifyContent: "space-between" }}>
          <Typography variant="h1">
            {datasetName ? `${datasetName} — Skor Trendi` : "Dataset Skor Trendi"}
          </Typography>
        </Box>
        {content}
      </Stack>
    </AppShell>
  );
}

export default DatasetTrendPage;
