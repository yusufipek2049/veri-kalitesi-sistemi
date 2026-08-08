import { useEffect, useMemo, useRef, useState } from "react";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import {
  Box,
  Divider,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  useTheme,
} from "@mui/material";
import type { EChartsCoreOption } from "echarts/core";
import type { TrendObservation } from "../dashboard/model";
import type { TrendComponents } from "../dashboard/model";
import { StatusBadge } from "./StatusBadge";

echarts.use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

interface TrendPanelProps {
  observations: TrendObservation[];
  description?: string;
  policyVersion?: string | null;
}

type TrendView = "chart" | "table";

function formatScore(value: number | null): string {
  return value === null ? "—" : value.toLocaleString("tr-TR", { maximumFractionDigits: 1 });
}

function formatTrendValue(value: number | null): string {
  if (value === null) return "Unknown";
  return value.toLocaleString("tr-TR", { maximumFractionDigits: 1 });
}

function renderTrendSummary(trend: TrendComponents, policyVersion: string | null | undefined) {
  const items = [
    { label: "Hareketli ortalama", value: formatTrendValue(trend.moving_average), status: trend.moving_average !== null ? "info" as const : "unknown" as const },
    { label: "Ardışık kötüleşme", value: trend.consecutive_deterioration_count !== null ? String(trend.consecutive_deterioration_count) : "Unknown", status: trend.consecutive_deterioration_count === null ? "unknown" as const : trend.consecutive_deterioration_count > 0 ? "warning" as const : "success" as const },
    { label: "Ani kötüleşme", value: trend.sudden_deterioration === null ? "Unknown" : trend.sudden_deterioration ? "Evet" : "Hayır", status: trend.sudden_deterioration === null ? "unknown" as const : trend.sudden_deterioration ? "critical" as const : "success" as const },
    { label: "Eşik altında kalma", value: trend.time_below_threshold_periods !== null ? `${trend.time_below_threshold_periods} dönem` : "Unknown", status: trend.time_below_threshold_periods === null ? "unknown" as const : trend.time_below_threshold_periods > 0 ? "warning" as const : "success" as const },
    { label: "İyileşme kalıcılığı", value: trend.improvement_persistence !== null ? `${trend.improvement_persistence} dönem` : "Unknown", status: trend.improvement_persistence === null ? "unknown" as const : trend.improvement_persistence > 0 ? "info" as const : "warning" as const },
  ];
  return (
    <Box sx={{ px: 4, py: 3 }}>
      <Divider sx={{ mb: 2 }} />
      <Box sx={{ mb: 2 }}>
        <Typography component="h3" variant="h4">Trend Bileşenleri</Typography>
      </Box>
      <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)" } }}>
        {items.map((item) => (
          <Box key={item.label} sx={{ alignItems: "center", display: "flex", gap: 1 }}>
            <Typography color="text.secondary" variant="body2">{item.label}:</Typography>
            {item.status === "unknown" ? (
              <Typography component="span" sx={{ fontStyle: "italic" }} variant="body2">Unknown</Typography>
            ) : (
              <StatusBadge label={item.value} tone={item.status} />
            )}
          </Box>
        ))}
      </Box>
      <Box sx={{ display: "flex", gap: 1, mt: 2 }}>
        <Typography color="text.secondary" variant="caption">Politika sürümü:</Typography>
        <Typography component="span" variant="caption">{policyVersion ?? "Unknown"}</Typography>
      </Box>
    </Box>
  );
}

export function TrendPanel({ observations, description = "Son 30 UTC gün · yalnız resmî skorlar", policyVersion }: TrendPanelProps) {
  const theme = useTheme();
  const [view, setView] = useState<TrendView>("chart");
  const chartElementRef = useRef<HTMLDivElement>(null);
  const officialObservations = useMemo(() => observations.filter((item) => item.official), [observations]);
  const hasTechnicalObservation = observations.some((item) => item.technicalStatus === "Teknik Hata");
  const latestTrend = useMemo(() => {
    for (let i = observations.length - 1; i >= 0; i--) {
      if (observations[i].trend) return observations[i].trend;
    }
    return null;
  }, [observations]);
  const versionBoundaryIndex = useMemo(() => observations.findIndex((item) => item.versionBoundary), [observations]);

  useEffect(() => {
    if (view !== "chart" || !chartElementRef.current) {
      return undefined;
    }

    const chart = echarts.init(chartElementRef.current, undefined, { renderer: "canvas" });
    const option: EChartsCoreOption = {
      animation: false,
      color: [theme.status.info, theme.palette.warning.main, theme.status.technical, theme.palette.success.main],
      grid: { left: 48, right: 88, top: 36, bottom: 44 },
      legend: {
        bottom: 0,
        data: [
          "Karşılaştırılabilir ham skor",
          "Hareketli ortalama",
          ...(hasTechnicalObservation ? ["Teknik hata"] : []),
          ...(observations.some((item) => !item.official && item.technicalStatus !== "Teknik Hata") ? ["Provizyonel / resmî değil"] : []),
        ],
        textStyle: { color: theme.palette.text.secondary },
      },
      tooltip: {
        trigger: "axis",
        formatter: (rawParams: unknown) => {
          const params = rawParams as Array<{ dataIndex: number }>;
          const item = observations[params[0]?.dataIndex ?? 0];
          if (!item) return "";
          return [
            `<strong>${item.displayDate}</strong>`,
            `Ham skor: ${formatScore(item.rawScore)}`,
            `Yeterlilik: ${item.qualification}`,
            `Kapsam: ${item.coverageRate === null ? "—" : `%${item.coverageRate}`}`,
            `Teknik durum: ${item.technicalStatus}`,
            item.versionBoundary ? "⚑ Sürüm sınırı" : "",
            item.trend?.moving_average != null ? `Hareketli ortalama: ${formatTrendValue(item.trend.moving_average)}` : "",
          ].filter(Boolean).join("<br />");
        },
      },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: observations.map((item) => item.displayDate),
        axisLine: { lineStyle: { color: theme.palette.divider } },
        axisLabel: { color: theme.palette.text.secondary },
      },
      yAxis: {
        type: "value",
        min: 60,
        max: 100,
        axisLabel: { color: theme.palette.text.secondary },
        splitLine: { lineStyle: { color: theme.palette.divider } },
      },
      series: [
        {
          name: "Karşılaştırılabilir ham skor",
          type: "line",
          connectNulls: false,
          symbol: "circle",
          symbolSize: 7,
          lineStyle: { width: 3, color: theme.status.info },
          itemStyle: { color: theme.palette.background.paper, borderColor: theme.status.info, borderWidth: 2 },
          data: observations.map((item) => (item.official ? item.rawScore : null)),
          ...(versionBoundaryIndex >= 0
            ? {
                markLine: {
                  silent: true,
                  symbol: "none",
                  lineStyle: { type: "dashed", color: theme.palette.warning.main, width: 2 },
                  data: [{ xAxis: observations[versionBoundaryIndex].displayDate }],
                  label: { formatter: "Sürüm sınırı", color: theme.palette.warning.main, fontSize: 11 },
                },
              }
            : {}),
        },
        {
          name: "Hareketli ortalama",
          type: "line",
          connectNulls: false,
          symbol: "none",
          lineStyle: { width: 2, type: "dashed", color: theme.palette.success.main },
          data: observations.map((item) => (item.official && item.trend?.moving_average != null ? item.trend.moving_average : null)),
        },
        {
          name: "Provizyonel / resmî değil",
          type: "line",
          showSymbol: true,
          symbol: "triangle",
          symbolSize: 10,
          lineStyle: { opacity: 0 },
          itemStyle: { color: theme.palette.warning.main },
          data: observations.map((item) => (!item.official && item.technicalStatus !== "Teknik Hata" ? item.rawScore : null)),
        },
        {
          name: "Teknik hata",
          type: "line",
          showSymbol: true,
          symbol: "diamond",
          symbolSize: 11,
          lineStyle: { opacity: 0 },
          itemStyle: { color: theme.status.technical },
          data: observations.map((item) => (item.technicalStatus === "Teknik Hata" ? 68 : null)),
        },
      ],
    };
    chart.setOption(option);

    const resizeObserver = new ResizeObserver(() => chart.resize());
    resizeObserver.observe(chartElementRef.current);
    return () => {
      resizeObserver.disconnect();
      chart.dispose();
    };
  }, [hasTechnicalObservation, observations, theme, view]);

  return (
    <Paper component="section" variant="outlined" aria-labelledby="trend-title" sx={{ borderRadius: 1.5, overflow: "hidden" }}>
      <Box sx={{ alignItems: "flex-start", display: "flex", flexWrap: "wrap", gap: 3, justifyContent: "space-between", px: 4, pt: 3 }}>
        <Box>
          <Typography id="trend-title" component="h2" variant="h3">Veri Kalitesi Trendi</Typography>
          <Typography color="text.secondary" variant="caption">{description}</Typography>
        </Box>
        <ToggleButtonGroup
          exclusive
          onChange={(_, next: TrendView | null) => next && setView(next)}
          size="small"
          value={view}
          aria-label="Trend görünümü"
        >
          <ToggleButton value="chart">Grafik</ToggleButton>
          <ToggleButton value="table">Tablo</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {view === "chart" ? (
        <Box
          ref={chartElementRef}
          role="img"
          aria-label={`Karşılaştırılabilir ham skor trendi ve hareketli ortalama. ${officialObservations.length} uyumlu resmî gözlem gösteriliyor. Teknik hata, provizyonel ve uyumsuz dönemler çizgiye katılmıyor. Sürüm sınırları kesikli çizgiyle işaretli.`}
          sx={(theme) => ({ height: theme.appLayout.chartHeight, mt: 2, width: "100%" })}
        />
      ) : (
        <TableContainer sx={(theme) => ({ maxHeight: theme.appLayout.tableMaxHeight, mt: 2 })}>
          <Table stickyHeader size="small" aria-label="Veri kalitesi trend tablosu">
            <caption>Grafikle aynı trend gözlemleri; resmî olmayan sonuçlar trende katılmaz.</caption>
            <TableHead>
              <TableRow>
                <TableCell>Dönem</TableCell>
                <TableCell align="right">Ham skor</TableCell>
                <TableCell align="right">Nihai skor</TableCell>
                <TableCell>Yeterlilik</TableCell>
                <TableCell>Teknik durum</TableCell>
                <TableCell>Trend kullanımı</TableCell>
                <TableCell align="right">Hareketli ortalama</TableCell>
                <TableCell>Sürüm sınırı</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {observations.map((item) => (
                <TableRow key={item.date}>
                  <TableCell>{item.displayDate}</TableCell>
                  <TableCell align="right">{formatScore(item.rawScore)}</TableCell>
                  <TableCell align="right">{formatScore(item.finalScore)}</TableCell>
                  <TableCell>{item.qualification}</TableCell>
                  <TableCell>
                    <StatusBadge
                      label={item.technicalStatus}
                      tone={item.technicalStatus === "Teknik Hata" ? "technical" : item.technicalStatus === "Hesaplanmadı" ? "unknown" : "success"}
                    />
                  </TableCell>
                  <TableCell>{item.official ? "Resmî" : "Dışlandı"}</TableCell>
                  <TableCell align="right">{item.trend?.moving_average != null ? formatTrendValue(item.trend.moving_average) : "Unknown"}</TableCell>
                  <TableCell>{item.versionBoundary ? "Evet" : "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
      {latestTrend && renderTrendSummary(latestTrend, policyVersion)}
    </Paper>
  );
}
