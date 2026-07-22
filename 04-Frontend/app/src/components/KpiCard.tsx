import { Box, Paper, Typography } from "@mui/material";
import type { KpiViewModel } from "../dashboard/model";
import { StatusBadge } from "./StatusBadge";

interface KpiCardProps {
  item: KpiViewModel;
}

export function KpiCard({ item }: KpiCardProps) {
  return (
    <Paper
      component="article"
      variant="outlined"
      aria-labelledby={`${item.id}-label`}
      sx={(theme) => ({
        borderColor: "divider",
        borderRadius: 1.5,
        display: "grid",
        gap: 3,
        minHeight: theme.appLayout.kpiMinHeight,
        p: 4,
        position: "relative",
        overflow: "hidden",
        "&::before": {
          bgcolor: theme.status[item.tone],
          content: '""',
          inset: 0,
          position: "absolute",
          width: theme.spacing(1),
        },
      })}
    >
      <Typography id={`${item.id}-label`} color="text.secondary" sx={{ fontWeight: 700 }} variant="body2">
        {item.label}
      </Typography>
      <Box sx={{ alignItems: "center", display: "flex", flexWrap: "wrap", gap: 3, justifyContent: "space-between", minWidth: 0 }}>
        <Typography
          component="p"
          sx={{ fontSize: 28, fontVariantNumeric: "tabular-nums", fontWeight: 800, lineHeight: 1 }}
        >
          {item.value}
        </Typography>
        <StatusBadge label={item.statusLabel} tone={item.tone} />
      </Box>
      <Typography color="text.secondary" sx={{ overflowWrap: "anywhere" }} variant="caption">
        {item.detail}
      </Typography>
    </Paper>
  );
}
