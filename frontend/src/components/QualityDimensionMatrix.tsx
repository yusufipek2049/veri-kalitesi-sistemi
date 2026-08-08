import { useEffect, useRef, useState } from "react";
import { BarChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import {
  Box,
  Button,
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
import type { QualityDimensionRowViewModel } from "../dashboard/model";
import type { StatusTone } from "../theme/tokens";
import { copyTableToClipboard } from "./exportTable";

echarts.use([BarChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

interface QualityDimensionMatrixProps {
  rows: QualityDimensionRowViewModel[];
}

type MatrixView = "chart" | "table";

const surfaceKey: Record<StatusTone, "criticalSurface" | "technicalSurface" | "warningSurface" | "successSurface" | "infoSurface" | "unknownSurface"> = {
  critical: "criticalSurface",
  technical: "technicalSurface",
  warning: "warningSurface",
  success: "successSurface",
  info: "infoSurface",
  unknown: "unknownSurface",
};

function formatScore(value: number | null): string {
  return value === null ? "—" : String(value);
}

export function QualityDimensionMatrix({ rows }: QualityDimensionMatrixProps) {
  const theme = useTheme();
  const [view, setView] = useState<MatrixView>("table");
  const chartElementRef = useRef<HTMLDivElement>(null);
  const dimensions = rows[0]?.cells.map((cell) => cell.dimension) ?? [];
  const fields = rows.map((row) => row.fieldLabel);

  const handleExport = () => {
    const headers = ["Veri alanı", ...dimensions, "Durum"];
    const tableRows = rows.map((row) => ({
      cells: [
        row.fieldLabel,
        ...row.cells.map((cell) => formatScore(cell.score)),
        row.cells.map((cell) => cell.statusLabel).join(" / "),
      ],
    }));
    copyTableToClipboard(headers, tableRows);
  };

  useEffect(() => {
    if (view !== "chart" || !chartElementRef.current || rows.length === 0) {
      return undefined;
    }

    const chart = echarts.init(chartElementRef.current, undefined, { renderer: "canvas" });
    const series = dimensions.map((dim, dimIndex) => ({
      name: dim,
      type: "bar" as const,
      data: rows.map((row) => row.cells[dimIndex]?.score ?? null),
      itemStyle: { color: theme.status.info },
    }));

    const option: EChartsCoreOption = {
      animation: false,
      grid: { left: 48, right: 24, top: 36, bottom: 60 },
      legend: {
        bottom: 0,
        data: dimensions,
        textStyle: { color: theme.palette.text.secondary },
      },
      tooltip: { trigger: "axis" },
      xAxis: {
        type: "category",
        data: fields,
        axisLine: { lineStyle: { color: theme.palette.divider } },
        axisLabel: { color: theme.palette.text.secondary },
      },
      yAxis: {
        type: "value",
        min: 0,
        max: 100,
        axisLabel: { color: theme.palette.text.secondary },
        splitLine: { lineStyle: { color: theme.palette.divider } },
      },
      series,
    };
    chart.setOption(option);

    const resizeObserver = new ResizeObserver(() => chart.resize());
    resizeObserver.observe(chartElementRef.current);
    return () => {
      resizeObserver.disconnect();
      chart.dispose();
    };
  }, [dimensions, fields, rows, theme, view]);

  return (
    <Paper component="section" variant="outlined" aria-labelledby="dimension-matrix-title" sx={{ borderRadius: 1.5, overflow: "hidden", minWidth: 0 }}>
      <Box sx={{ alignItems: "flex-start", display: "flex", flexWrap: "wrap", gap: 3, justifyContent: "space-between", px: 4, pt: 3 }}>
        <Box>
          <Typography id="dimension-matrix-title" component="h2" variant="h3">Kalite Boyutu Matrisi</Typography>
          <Typography color="text.secondary" variant="caption">Sentetik veri alanı × kalite boyutu</Typography>
        </Box>
        <Box sx={{ alignItems: "center", display: "flex", gap: 2 }}>
          <ToggleButtonGroup
            exclusive
            onChange={(_, next: MatrixView | null) => next && setView(next)}
            size="small"
            value={view}
            aria-label="Kalite boyutu matrisi görünümü"
          >
            <ToggleButton value="chart">Grafik</ToggleButton>
            <ToggleButton value="table">Tablo</ToggleButton>
          </ToggleButtonGroup>
          {view === "table" && rows.length > 0 && (
            <Button onClick={handleExport} size="small" variant="outlined">
              Tabloyu kopyala
            </Button>
          )}
        </Box>
      </Box>

      {rows.length === 0 ? (
        <Box sx={(theme) => ({ bgcolor: theme.status.unknownSurface, borderRadius: 1, mt: 4, mx: 4, p: 3 })}>
          <Typography color="text.secondary" variant="body2">Boyut matrisi bu API kapsamında sağlanmıyor.</Typography>
        </Box>
      ) : view === "chart" ? (
        <Box
          ref={chartElementRef}
          role="img"
          aria-label={`Kalite boyutu matrisi grafiği. ${fields.length} veri alanı ve ${dimensions.length} boyut.`}
          sx={(theme) => ({ height: theme.appLayout.chartHeight, mt: 2, width: "100%" })}
        />
      ) : (
        <TableContainer sx={{ mt: 2 }}>
          <Table size="small" aria-label="Sentetik kalite boyutu matrisi" sx={{ tableLayout: "fixed", width: "100%" }}>
            <caption>Renklerin yanında her hücrede sayısal skor veya hesaplanmadı işareti bulunur.</caption>
            <TableHead>
              <TableRow>
                <TableCell sx={{ px: 1, py: 1, typography: "caption", width: (theme) => theme.spacing(18) }}>Veri alanı</TableCell>
                {dimensions.map((dimension) => (
                  <TableCell align="center" key={dimension} sx={{ px: 1, py: 1, typography: "caption", whiteSpace: "nowrap" }}>
                    {dimension}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.fieldId}>
                  <TableCell component="th" scope="row" sx={{ px: 1, py: 1, typography: "caption" }}>{row.fieldLabel}</TableCell>
                  {row.cells.map((cell) => (
                    <TableCell align="center" key={cell.dimension} sx={{ p: 1 }}>
                      <Box
                        aria-label={`${row.fieldLabel}, ${cell.dimension}: ${cell.score ?? "Hesaplanmadı"}, ${cell.statusLabel}`}
                        sx={(theme) => ({
                          bgcolor: theme.status[surfaceKey[cell.tone]],
                          borderRadius: 1,
                          color: theme.status[cell.tone],
                          fontVariantNumeric: "tabular-nums",
                          fontSize: theme.typography.caption.fontSize,
                          fontWeight: 700,
                          px: 1,
                          py: 1.5,
                        })}
                      >
                        {cell.score ?? "—"}
                      </Box>
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Paper>
  );
}
