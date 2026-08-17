import { useState } from "react";
import {
  IconButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Tooltip,
} from "@mui/material";
import {
  BadgeCheck,
  FileCheck,
  LoaderCircle,
  MoreVertical,
  SearchCheck,
  ShieldCheck,
  UserRoundPen,
  type LucideIcon,
} from "lucide-react";
import type { IssueListItem } from "./model";

export type IssueRowAction = "START_INVESTIGATION" | "REASSIGN" | "RESOLVE" | "VERIFY" | "CLOSE";

const actionMenuEntries: Array<{ action: IssueRowAction; label: string; icon: LucideIcon }> = [
  { action: "START_INVESTIGATION", label: "İncelemeye al", icon: SearchCheck },
  { action: "REASSIGN", label: "Yeniden ata", icon: UserRoundPen },
  { action: "RESOLVE", label: "Çözüm kaydet", icon: FileCheck },
  { action: "VERIFY", label: "Doğrula", icon: ShieldCheck },
  { action: "CLOSE", label: "Kapat", icon: BadgeCheck },
];

export function IssueActionMenu({
  item,
  mutationPending,
  onAction,
}: {
  item: IssueListItem;
  mutationPending: boolean;
  onAction: (action: IssueRowAction) => void;
}) {
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);
  const closeMenu = () => setMenuAnchor(null);
  return (
    <>
      <Tooltip title="Sorun işlemleri">
        <span>
          <IconButton
            aria-label={`${item.issueNo} işlemleri`}
            disabled={mutationPending}
            onClick={(event) => setMenuAnchor(event.currentTarget)}
            size="small"
          >
            {mutationPending
              ? <LoaderCircle aria-hidden="true" size={18} />
              : <MoreVertical aria-hidden="true" size={18} />}
          </IconButton>
        </span>
      </Tooltip>
      <Menu
        anchorEl={menuAnchor}
        onClose={closeMenu}
        open={Boolean(menuAnchor)}
      >
        {actionMenuEntries
          .filter((entry) => item.availableActions.includes(entry.action))
          .map(({ action, label, icon: Icon }) => (
            <MenuItem
              key={action}
              onClick={() => {
                closeMenu();
                onAction(action);
              }}
            >
              <ListItemIcon><Icon aria-hidden="true" size={16} /></ListItemIcon>
              <ListItemText>{label}</ListItemText>
            </MenuItem>
          ))}
      </Menu>
    </>
  );
}
