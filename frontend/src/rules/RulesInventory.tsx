import { Box, Paper, Typography } from "@mui/material";
import type { RuleAction, RuleListItem } from "./model";
import { RuleRow } from "./RuleRow";

interface RulesInventoryProps {
  items: RuleListItem[];
  onAction: (item: RuleListItem, action: RuleAction) => void;
  actionLoading: string | null;
  catalogDatasets?: { id: string; name: string; namespace: string }[];
}

export function RulesInventory({ items, onAction, actionLoading, catalogDatasets }: RulesInventoryProps) {
  return (
    <Paper component="section" sx={{ borderRadius: 1.5, overflow: "hidden" }} variant="outlined">
      <Box sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
        <Typography component="h2" variant="h3">Kural Envanteri</Typography>
        <Typography color="text.secondary" variant="body2">{items.length} kural</Typography>
      </Box>
      <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
        {items.map((item) => (
          <RuleRow
            item={item}
            key={item.id}
            onAction={onAction}
            actionLoading={actionLoading}
            catalogDatasets={catalogDatasets}
          />
        ))}
      </Box>
    </Paper>
  );
}
