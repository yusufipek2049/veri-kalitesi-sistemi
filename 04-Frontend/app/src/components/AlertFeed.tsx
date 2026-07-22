import { Box, Button, Divider, Paper, Typography } from "@mui/material";
import type { AlertViewModel } from "../dashboard/model";
import { StatusBadge } from "./StatusBadge";

interface AlertFeedProps {
  items: AlertViewModel[];
}

export function AlertFeed({ items }: AlertFeedProps) {
  return (
    <Paper component="section" variant="outlined" aria-labelledby="alert-feed-title" sx={{ borderRadius: 1.5, height: "100%", overflow: "hidden" }}>
      <Box sx={{ alignItems: "center", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
        <Box>
          <Typography id="alert-feed-title" component="h2" variant="h3">Kritik Alarm Akışı</Typography>
          <Typography color="text.secondary" variant="caption">Son 24 saat · sentetik kayıtlar</Typography>
        </Box>
        <Button size="small" variant="text">Tümünü gör</Button>
      </Box>
      <Divider />
      <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
        {items.map((alert, index) => (
          <Box component="li" key={alert.id}>
            <Box sx={{ alignItems: "start", display: "grid", gap: 2, gridTemplateColumns: "auto minmax(0, 1fr) auto", px: 4, py: 3 }}>
              <StatusBadge label={alert.statusLabel} tone={alert.tone} />
              <Box sx={{ minWidth: 0 }}>
                <Typography sx={{ display: "block", fontWeight: 700, overflowWrap: "anywhere" }} variant="body2">{alert.title}</Typography>
                <Typography color="text.secondary" sx={{ display: "block", overflowWrap: "anywhere" }} variant="caption">{alert.scope}</Typography>
                <Button size="small" sx={{ display: "flex", mt: 1, p: 0 }} variant="text">{alert.nextAction}</Button>
              </Box>
              <Typography color="text.secondary" sx={{ whiteSpace: "nowrap" }} variant="caption">{alert.time}</Typography>
            </Box>
            {index < items.length - 1 ? <Divider /> : null}
          </Box>
        ))}
      </Box>
    </Paper>
  );
}
