import { useEffect, useMemo, useRef, useState } from "react";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import {
  Box,
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
} from "@mui/material";
import type { EChartsCoreOption } from "echarts/core";
import type { TrendObservation } from "../dashboard/model";
import { designTokens } from "../theme/tokens";
import { StatusBadge } from "./StatusBadge";

echarts.use([LineChart, GridComponent, LegendComponent, MarkLineComponent, TooltipComponent, CanvasRenderer]);

interface TrendPanelProps {
  observations: TrendObservation[];
  description?: string;
}

type TrendView = "chart" | "table";

function formatScore(value: number | null): string {
  return value === null ? "—" : value.toLocaleString("tr-TR", { maximumFractionDigits: 1 });
}

export function TrendPanel({ observations, description = "Son 30 UTC gün · yalnız resmî skorlar" }: TrendPanelProps) {
  const [view, setView] = useState<TrendView>("chart");
  const chartElementRef = useRef<HTMLDivElement>(null);
  const officialObservations = useMemo(() => observations.filter((item) => item.official), [observations]);
  const hasTechnicalObservation = observations.some((item) => item.technicalStatus === "Teknik Hata");

  useEffect(() => {
    if (view !== "chart" || !chartElementRef.current) {
      return undefined;
    }

    const chart = echarts.init(chartElementRef.current, undefined, { renderer: "canvas" });
    const option: EChartsCoreOption = {
      animation: false,
      color: [designTokens.color.status.info, designTokens.color.status.technical],
      grid: { left: 48, right: 88, top: 36, bottom: 44 },
      legend: {
        bottom: 0,
        data: hasTechnicalObservation ? ["Resmî nihai skor", "Teknik hata"] : ["Resmî nihai skor"],
        textStyle: { color: designTokens.color.text.muted },
      },
      tooltip: {
        trigger: "axis",
        formatter: (rawParams: unknown) => {
          const params = rawParams as Array<{ dataIndex: number }>;
          const item = observations[params[0]?.dataIndex ?? 0];
          if (!item) return "";
          return [
            `<strong>${item.displayDate}</strong>`,
            `Nihai skor: ${formatScore(item.finalScore)}`,
            `Yeterlilik: ${item.qualification}`,
            `Kapsam: ${item.coverageRate === null ? "—" : `%${item.coverageRate}`}`,
            `Teknik durum: ${item.technicalStatus}`,
          ].join("<br />");
        },
      },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: observations.map((item) => item.displayDate),
        axisLine: { lineStyle: { color: designTokens.color.border } },
        axisLabel: { color: designTokens.color.text.muted },
      },
      yAxis: {
        type: "value",
        min: 60,
        max: 100,
        axisLabel: { color: designTokens.color.text.muted },
        splitLine: { lineStyle: { color: designTokens.color.border } },
      },
      series: [
        {
          name: "Resmî nihai skor",
          type: "line",
          connectNulls: false,
          symbol: "circle",
          symbolSize: 7,
          lineStyle: { width: 3, color: designTokens.color.status.info },
          itemStyle: { color: designTokens.color.surface, borderColor: designTokens.color.status.info, borderWidth: 2 },
          data: observations.map((item) => (item.official ? item.finalScore : null)),
          markLine: {
            symbol: "none",
            label: { formatter: "Kritik eşik 70", color: designTokens.color.status.critical, position: "insideEndTop" },
            lineStyle: { color: designTokens.color.status.critical, type: "dashed" },
            data: [{ yAxis: 70 }],
          },
        },
        {
          name: "Teknik hata",
          type: "line",
          showSymbol: true,
          symbol: "diamond",
          symbolSize: 11,
          lineStyle: { opacity: 0 },
          itemStyle: { color: designTokens.color.status.technical },
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
  }, [hasTechnicalObservation, observations, view]);

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
          aria-label={`Resmî nihai skor trendi. ${officialObservations.length} resmî gözlem gösteriliyor. Teknik hata ve provizyonel sonuçlar çizgiye katılmıyor.`}
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
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Paper>
  );
}
