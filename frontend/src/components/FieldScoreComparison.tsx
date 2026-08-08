import { useState } from "react";
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
} from "@mui/material";
import type { FieldScoreViewModel } from "../dashboard/model";
import { StatusBadge } from "./StatusBadge";
import { copyTableToClipboard } from "./exportTable";

interface FieldScoreComparisonProps {
  items: FieldScoreViewModel[];
}

type FieldScoreView = "chart" | "table";

function formatScore(value: number | null): string {
  return value === null ? "—" : value.toLocaleString("tr-TR");
}

export function FieldScoreComparison({ items }: FieldScoreComparisonProps) {
  const [view, setView] = useState<FieldScoreView>("chart");

  const handleExport = () => {
    copyTableToClipboard(
      ["Veri alanı", "Skor", "Durum"],
      items.map((item) => ({
        cells: [item.label, formatScore(item.score), item.statusLabel],
      })),
    );
  };

  return (
    <Paper component="section" variant="outlined" aria-labelledby="field-score-title" sx={{ borderRadius: 1.5, overflow: "hidden" }}>
      <Box sx={{ alignItems: "flex-start", display: "flex", flexWrap: "wrap", gap: 3, justifyContent: "space-between", px: 4, pt: 3 }}>
        <Box>
          <Typography id="field-score-title" component="h2" variant="h3">Veri Alanı Bazlı Skorlar</Typography>
          <Typography color="text.secondary" variant="caption">Sentetik karşılaştırma · yüksekten düşüğe</Typography>
        </Box>
        <Box sx={{ alignItems: "center", display: "flex", gap: 2 }}>
          <ToggleButtonGroup
            exclusive
            onChange={(_, next: FieldScoreView | null) => next && setView(next)}
            size="small"
            value={view}
            aria-label="Veri alanı skorları görünümü"
          >
            <ToggleButton value="chart">Grafik</ToggleButton>
            <ToggleButton value="table">Tablo</ToggleButton>
          </ToggleButtonGroup>
          {view === "table" && items.length > 0 && (
            <Button onClick={handleExport} size="small" variant="outlined">
              Tabloyu kopyala
            </Button>
          )}
        </Box>
      </Box>

      {items.length === 0 ? (
        <Box sx={(theme) => ({ bgcolor: theme.status.unknownSurface, borderRadius: 1, mt: 4, mx: 4, p: 3 })}>
          <Typography color="text.secondary" variant="body2">Karşılaştırma verisi bu API kapsamında sağlanmıyor.</Typography>
        </Box>
      ) : view === "chart" ? (
        <Box component="ul" sx={{ display: "grid", gap: 3, listStyle: "none", m: 0, mt: 4, mx: 4, pb: 4, p: 0 }}>
          {items.map((item) => (
            <Box component="li" key={item.id} sx={{ alignItems: "center", display: "grid", gap: 3, gridTemplateColumns: "minmax(88px, auto) minmax(120px, 1fr) 48px" }}>
              <Typography variant="body2">{item.label}</Typography>
              <Box
                aria-label={`${item.label}: ${item.score === null ? item.statusLabel : `${item.score.toLocaleString("tr-TR")} puan, ${item.statusLabel}`}`}
                aria-valuemax={100}
                aria-valuemin={0}
                aria-valuenow={item.score ?? undefined}
                role="progressbar"
                sx={(theme) => ({
                  bgcolor: theme.status.unknownSurface,
                  borderRadius: 1,
                  height: theme.spacing(2),
                  overflow: "hidden",
                })}
              >
                {item.score !== null ? (
                  <Box
                    aria-hidden="true"
                    sx={(theme) => ({
                      bgcolor: theme.status[item.tone],
                      height: "100%",
                      width: `${item.score}%`,
                    })}
                  />
                ) : null}
              </Box>
              <Typography align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 700 }} variant="body2">
                {item.score === null ? "—" : item.score.toLocaleString("tr-TR")}
              </Typography>
            </Box>
          ))}
        </Box>
      ) : (
        <TableContainer sx={(theme) => ({ maxHeight: theme.appLayout.tableMaxHeight, mt: 2 })}>
          <Table stickyHeader size="small" aria-label="Veri alanı bazlı skorlar tablosu">
            <caption>Veri alanı skorları; grafik görünümle aynı verileri içerir.</caption>
            <TableHead>
              <TableRow>
                <TableCell>Veri alanı</TableCell>
                <TableCell align="right">Skor</TableCell>
                <TableCell>Durum</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.label}</TableCell>
                  <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                    {formatScore(item.score)}
                  </TableCell>
                  <TableCell>
                    <StatusBadge label={item.statusLabel} tone={item.tone} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Paper>
  );
}
