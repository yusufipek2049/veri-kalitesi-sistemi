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
import { copyTableToClipboard } from "./exportTable";

interface ContributionComponent {
  component_ref: string;
  component_type: "RULE" | "DATASET" | "DIMENSION" | "SOURCE" | "UNKNOWN";
  included: boolean;
  weight: string | null;
  contribution: string | null;
  exclusion_reason: string | null;
}

interface ScoreContributionPanelProps {
  components?: ContributionComponent[];
  profileVersion?: string | null;
  evidenceReferences?: string[];
  diagnosisStatus?: string;
  diagnosisEvidenceRef?: string | null;
}

type ContributionView = "chart" | "table";

function formatValue(value: string | null): string {
  return value ?? "—";
}

export function ScoreContributionPanel({
  components = [],
  profileVersion,
  evidenceReferences,
  diagnosisStatus,
  diagnosisEvidenceRef,
}: ScoreContributionPanelProps) {
  const theme = useTheme();
  const [view, setView] = useState<ContributionView>("chart");
  const chartElementRef = useRef<HTMLDivElement>(null);

  const includedComponents = components.filter((c) => c.included);

  const handleExport = () => {
    const headers = ["Bileşen", "Tip", "Dahil", "Ağırlık", "Katkı", "Dışlama nedeni"];
    const tableRows = components.map((c) => ({
      cells: [
        c.component_ref,
        c.component_type,
        c.included ? "Evet" : "Hayır",
        formatValue(c.weight),
        formatValue(c.contribution),
        formatValue(c.exclusion_reason),
      ],
    }));
    copyTableToClipboard(headers, tableRows);
  };

  useEffect(() => {
    if (view !== "chart" || !chartElementRef.current || includedComponents.length === 0) {
      return undefined;
    }

    const chart = echarts.init(chartElementRef.current, undefined, { renderer: "canvas" });
    const option: EChartsCoreOption = {
      animation: false,
      grid: { left: 120, right: 24, top: 16, bottom: 24 },
      tooltip: { trigger: "axis" },
      xAxis: {
        type: "value",
        axisLabel: { color: theme.palette.text.secondary },
        splitLine: { lineStyle: { color: theme.palette.divider } },
      },
      yAxis: {
        type: "category",
        data: includedComponents.map((c) => c.component_ref),
        axisLine: { lineStyle: { color: theme.palette.divider } },
        axisLabel: { color: theme.palette.text.secondary },
      },
      series: [
        {
          name: "Katkı",
          type: "bar",
          data: includedComponents.map((c) => {
            const value = c.contribution !== null ? Number(c.contribution) : null;
            return Number.isFinite(value) ? value : null;
          }),
          itemStyle: { color: theme.status.info },
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
  }, [includedComponents, theme, view]);

  return (
    <Paper component="section" variant="outlined" sx={{ borderRadius: 1.5, overflow: "hidden", p: 4 }}>
      <Box sx={{ alignItems: "flex-start", display: "flex", flexWrap: "wrap", gap: 3, justifyContent: "space-between" }}>
        <Box>
          <Typography component="h2" variant="h3">Skor Katkı Grafiği</Typography>
        </Box>
        {components.length > 0 && (
          <Box sx={{ alignItems: "center", display: "flex", gap: 2 }}>
            <ToggleButtonGroup
              exclusive
              onChange={(_, next: ContributionView | null) => next && setView(next)}
              size="small"
              value={view}
              aria-label="Skor katkısı görünümü"
            >
              <ToggleButton value="chart">Grafik</ToggleButton>
              <ToggleButton value="table">Tablo</ToggleButton>
            </ToggleButtonGroup>
            {view === "table" && (
              <Button onClick={handleExport} size="small" variant="outlined">
                Tabloyu kopyala
              </Button>
            )}
          </Box>
        )}
      </Box>

      {components.length === 0 ? (
        <Typography color="text.secondary" sx={{ mt: 2 }} variant="body2">
          Katkı kanıtı Unknown. Ham kayıt, serbest SQL veya hassas değer gösterilmedi.
        </Typography>
      ) : view === "chart" ? (
        <>
          {includedComponents.length === 0 ? (
            <Typography color="text.secondary" sx={{ mt: 2 }} variant="body2">
              Katkı kanıtı Unknown. Ham kayıt, serbest SQL veya hassas değer gösterilmedi.
            </Typography>
          ) : (
            <Box
              ref={chartElementRef}
              role="img"
              aria-label={`Skor katkı grafiği. ${includedComponents.length} bileşen gösteriliyor.`}
              sx={(theme) => ({ height: theme.appLayout.chartHeight, mt: 2, width: "100%" })}
            />
          )}
        </>
      ) : (
        <TableContainer sx={(theme) => ({ maxHeight: theme.appLayout.tableMaxHeight, mt: 2 })}>
          <Table stickyHeader size="small" aria-label="Skor katkı tablosu">
            <caption>Dahil bileşenlerin ağırlık ve katkı değerleri; dışlanan bileşenlerin nedeni.</caption>
            <TableHead>
              <TableRow>
                <TableCell>Bileşen</TableCell>
                <TableCell>Tip</TableCell>
                <TableCell>Dahil</TableCell>
                <TableCell align="right">Ağırlık</TableCell>
                <TableCell align="right">Katkı</TableCell>
                <TableCell>Dışlama nedeni</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {components.map((c) => (
                <TableRow key={c.component_ref}>
                  <TableCell>{c.component_ref}</TableCell>
                  <TableCell>{c.component_type}</TableCell>
                  <TableCell>{c.included ? "Evet" : "Hayır"}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                    {formatValue(c.weight)}
                  </TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                    {formatValue(c.contribution)}
                  </TableCell>
                  <TableCell>{formatValue(c.exclusion_reason)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Typography color="text.secondary" sx={{ mt: 2 }} variant="body2">
        Profil sürümü: {profileVersion ?? "UNKNOWN"}
      </Typography>
      <Typography color="text.secondary" sx={{ mt: 1 }} variant="body2">
        Güvenli kanıt referansları: {evidenceReferences?.length
          ? evidenceReferences.join(", ")
          : "UNKNOWN"}
      </Typography>
      <Typography color="text.secondary" sx={{ mt: 1 }} variant="body2">
        Kanıtlı teşhis: {diagnosisStatus ?? "UNKNOWN"}
        {diagnosisEvidenceRef ? ` (${diagnosisEvidenceRef})` : ""}
      </Typography>
    </Paper>
  );
}
