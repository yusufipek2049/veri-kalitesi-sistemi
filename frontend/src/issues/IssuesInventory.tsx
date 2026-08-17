import { Box, Paper, Typography } from "@mui/material";
import type { IssueRowAction } from "./IssueActionMenu";
import { IssueRow } from "./IssueRow";
import type { IssueListItem } from "./model";

export function IssuesInventory({
  items,
  pendingIssueId,
  onAction,
}: {
  items: IssueListItem[];
  pendingIssueId?: string;
  onAction: (action: IssueRowAction, item: IssueListItem) => void;
}) {
  return (
    <Paper component="section" sx={{ borderRadius: 1.5, overflow: "hidden" }} variant="outlined">
      <Box sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
        <Typography component="h2" variant="h3">Sorun Envanteri</Typography>
        <Typography color="text.secondary" variant="body2">{items.length} kayıt · en fazla 100</Typography>
      </Box>
      <Box
        aria-hidden="true"
        sx={{
          borderBottom: 1,
          borderColor: "divider",
          color: "text.secondary",
          display: { xs: "none", lg: "grid" },
          fontSize: "caption.fontSize",
          fontWeight: 700,
          gap: 3,
          gridTemplateColumns: "40px minmax(210px, 1fr) minmax(130px, .58fr) minmax(110px, .48fr) minmax(170px, .72fr) minmax(155px, .65fr) minmax(150px, .6fr)",
          px: 4,
          py: 2,
        }}
      >
        <Box />
        <Box>Sorun</Box>
        <Box>Durum</Box>
        <Box>Öncelik</Box>
        <Box>Kapsam ve tür</Box>
        <Box>Son hareket</Box>
        <Box>İşlem</Box>
      </Box>
      <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
        {items.map((item) => (
          <IssueRow
            item={item}
            key={item.id}
            mutationPending={pendingIssueId === item.id}
            onAction={onAction}
          />
        ))}
      </Box>
    </Paper>
  );
}
