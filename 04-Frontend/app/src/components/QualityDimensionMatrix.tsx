import { Box, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import type { QualityDimensionRowViewModel } from "../dashboard/model";
import type { StatusTone } from "../theme/tokens";

interface QualityDimensionMatrixProps {
  rows: QualityDimensionRowViewModel[];
}

const surfaceKey: Record<StatusTone, "criticalSurface" | "technicalSurface" | "warningSurface" | "successSurface" | "infoSurface" | "unknownSurface"> = {
  critical: "criticalSurface",
  technical: "technicalSurface",
  warning: "warningSurface",
  success: "successSurface",
  info: "infoSurface",
  unknown: "unknownSurface",
};

export function QualityDimensionMatrix({ rows }: QualityDimensionMatrixProps) {
  const dimensions = rows[0]?.cells.map((cell) => cell.dimension) ?? [];
  return (
    <Paper component="section" variant="outlined" aria-labelledby="dimension-matrix-title" sx={{ borderRadius: 1.5, minWidth: 0, p: 4 }}>
      <Typography id="dimension-matrix-title" component="h2" variant="h3">Kalite Boyutu Matrisi</Typography>
      <Typography color="text.secondary" variant="caption">Sentetik veri alanı × kalite boyutu</Typography>

      {rows.length === 0 ? (
        <Box sx={(theme) => ({ bgcolor: theme.status.unknownSurface, borderRadius: 1, mt: 4, p: 3 })}>
          <Typography color="text.secondary" variant="body2">Boyut matrisi bu API kapsamında sağlanmıyor.</Typography>
        </Box>
      ) : (
        <TableContainer sx={{ mt: 3 }}>
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
