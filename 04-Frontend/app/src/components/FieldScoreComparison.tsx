import { Box, Paper, Typography } from "@mui/material";
import type { FieldScoreViewModel } from "../dashboard/model";

interface FieldScoreComparisonProps {
  items: FieldScoreViewModel[];
}

export function FieldScoreComparison({ items }: FieldScoreComparisonProps) {
  return (
    <Paper component="section" variant="outlined" aria-labelledby="field-score-title" sx={{ borderRadius: 1.5, p: 4 }}>
      <Typography id="field-score-title" component="h2" variant="h3">Veri Alanı Bazlı Skorlar</Typography>
      <Typography color="text.secondary" variant="caption">Sentetik karşılaştırma · yüksekten düşüğe</Typography>

      {items.length === 0 ? (
        <Box sx={(theme) => ({ bgcolor: theme.status.unknownSurface, borderRadius: 1, mt: 4, p: 3 })}>
          <Typography color="text.secondary" variant="body2">Karşılaştırma verisi bu API kapsamında sağlanmıyor.</Typography>
        </Box>
      ) : (
        <Box component="ul" sx={{ display: "grid", gap: 3, listStyle: "none", m: 0, mt: 4, p: 0 }}>
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
      )}
    </Paper>
  );
}
