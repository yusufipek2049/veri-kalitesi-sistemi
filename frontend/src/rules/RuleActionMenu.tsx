import { useState } from "react";
import {
  Box,
  IconButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Tooltip,
  Typography,
} from "@mui/material";
import { LoaderCircle, MoreVertical } from "lucide-react";
import { actionIcons, actionLabels } from "./labels";
import type { RuleAction, RuleListItem } from "./model";

interface RuleActionMenuProps {
  item: RuleListItem;
  loading: boolean;
  onAction: (item: RuleListItem, action: RuleAction) => void;
}

export function RuleActionMenu({ item, loading, onAction }: RuleActionMenuProps) {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleAction = (action: RuleAction) => {
    setAnchorEl(null);
    onAction(item, action);
  };

  return (
    <Box>
      <Tooltip title="Eylemler">
        <IconButton
          aria-label={`${item.name} için eylemler`}
          data-testid="rule-actions-trigger"
          disabled={loading}
          onClick={handleClick}
          size="small"
        >
          {loading ? (
            <LoaderCircle aria-hidden="true" size={18} />
          ) : (
            <MoreVertical aria-hidden="true" size={18} />
          )}
        </IconButton>
      </Tooltip>
      <Menu
        anchorEl={anchorEl}
        anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
        onClose={() => setAnchorEl(null)}
        open={open}
        slotProps={{ paper: { sx: { minWidth: 200 } } }}
        transformOrigin={{ horizontal: "right", vertical: "top" }}
      >
        {item.availableActions.map((action) => {
          const ActionIcon = actionIcons[action];
          return (
            <MenuItem
              key={action}
              data-testid={`rule-action-${action}`}
              onClick={() => handleAction(action)}
            >
              <ListItemIcon>
                <ActionIcon aria-hidden="true" size={18} />
              </ListItemIcon>
              <ListItemText>{actionLabels[action]}</ListItemText>
            </MenuItem>
          );
        })}
        {item.availableActions.length === 0 && (
          <MenuItem disabled>
            <ListItemText>
              <Typography color="text.secondary" variant="body2">
                Kullanılabilir eylem yok
              </Typography>
            </ListItemText>
          </MenuItem>
        )}
      </Menu>
    </Box>
  );
}
