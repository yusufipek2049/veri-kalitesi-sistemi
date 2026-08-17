import { Box, Typography } from "@mui/material";
import {
  AlertTriangle,
  BadgeCheck,
  Ban,
  CircleDot,
  CircleEllipsis,
  ShieldAlert,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router-dom";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens, type StatusTone } from "../theme/tokens";
import { IssueActionMenu, type IssueRowAction } from "./IssueActionMenu";
import { priorityLabels, statusLabels, triggerLabels } from "./labels";
import type { IssueListItem } from "./model";

function statusTone(status: string): StatusTone {
  if (status === "RESOLVED" || status === "VERIFIED") return "success";
  if (status === "INVESTIGATING" || status === "ASSIGNED") return "info";
  if (status === "WAITING_FOR_RESOLUTION") return "warning";
  return "unknown";
}

function priorityTone(priority: string): StatusTone {
  if (priority === "CRITICAL") return "critical";
  if (priority === "HIGH") return "warning";
  if (priority === "MEDIUM") return "info";
  return "unknown";
}

function issuePresentation(item: IssueListItem): { icon: LucideIcon; tone: StatusTone } {
  if (item.sourceEventType === "TECHNICAL") return { icon: Wrench, tone: "technical" };
  if (item.priority === "CRITICAL") return { icon: ShieldAlert, tone: "critical" };
  if (item.status === "VERIFIED" || item.status === "RESOLVED") {
    return { icon: BadgeCheck, tone: "success" };
  }
  if (item.status === "CANCELLED") return { icon: Ban, tone: "unknown" };
  if (item.status === "INVESTIGATING") return { icon: CircleEllipsis, tone: "info" };
  if (item.priority === "HIGH") return { icon: AlertTriangle, tone: "warning" };
  return { icon: CircleDot, tone: "info" };
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function ScopeLink({ item }: { item: IssueListItem }) {
  const displayName = item.scopeDisplayName ?? item.scopeId;
  const linkTarget = item.scopeType === "DATASET"
    ? `/catalog/datasets/${item.scopeId}`
    : item.scopeType === "SOURCE"
      ? "/data-sources"
      : null;

  return (
    <Box sx={{ minWidth: 0 }}>
      {linkTarget ? (
        <Typography
          component={Link}
          noWrap
          sx={{
            color: "primary.main",
            fontWeight: 500,
            textDecoration: "none",
            "&:hover": { textDecoration: "underline" },
          }}
          to={linkTarget}
          variant="body2"
        >
          {displayName}
        </Typography>
      ) : (
        <Typography
          noWrap
          sx={{
            fontWeight: 500,
          }}
          variant="body2"
        >
          {displayName}
        </Typography>
      )}
      <Typography color="text.secondary" variant="caption">
        {item.scopeType === "SOURCE" ? "Veri kaynağı" : "Dataset"}
        {item.sourceRuleVersionId ? ` · Kural: ${item.sourceRuleVersionId.slice(0, 8)}…` : ""}
        {item.sourceExecutionId ? ` · ${item.sourceEventType === "TECHNICAL" ? "Teknik" : "Kalite"}` : ""}
      </Typography>
    </Box>
  );
}

function RowBadgeCells({ item }: { item: IssueListItem }) {
  return (
    <>
      <Box
        sx={{
          gridColumn: { xs: "2", md: "3", lg: "auto" },
          justifySelf: { md: "end", lg: "start" },
        }}
      >
        <Typography color="text.secondary" sx={{ display: { xs: "block", lg: "none" } }} variant="caption">
          Durum
        </Typography>
        <StatusBadge
          label={statusLabels[item.status] ?? item.status}
          tone={statusTone(item.status)}
        />
      </Box>
      <Box sx={{ gridColumn: { xs: "2", md: "2", lg: "auto" } }}>
        <Typography color="text.secondary" sx={{ display: { xs: "block", lg: "none" } }} variant="caption">
          Öncelik
        </Typography>
        <StatusBadge
          label={priorityLabels[item.priority] ?? item.priority}
          tone={priorityTone(item.priority)}
        />
      </Box>
    </>
  );
}

export function IssueRow({
  item,
  mutationPending,
  onAction,
}: {
  item: IssueListItem;
  mutationPending: boolean;
  onAction: (action: IssueRowAction, item: IssueListItem) => void;
}) {
  const presentation = issuePresentation(item);
  const Icon = presentation.icon;
  const hasActions = item.availableActions.length > 0;
  return (
    <Box
      component="li"
      sx={{
        alignItems: "center",
        borderBottom: 1,
        borderColor: "divider",
        display: "grid",
        gap: 3,
        gridTemplateColumns: {
          xs: "40px minmax(0, 1fr)",
          md: "40px minmax(210px, 1fr) minmax(155px, auto)",
          lg: "40px minmax(210px, 1fr) minmax(130px, .58fr) minmax(110px, .48fr) minmax(170px, .72fr) minmax(155px, .65fr) minmax(150px, .6fr)",
        },
        minHeight: 88,
        px: 4,
        py: 3,
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Box
        aria-hidden="true"
        data-testid="issue-icon-slot"
        sx={(theme) => ({
          alignItems: "center",
          bgcolor: theme.status[`${presentation.tone}Surface`],
          borderRadius: 1,
          color: theme.status[presentation.tone],
          display: "flex",
          height: 40,
          justifyContent: "center",
          width: 40,
        })}
      >
        <Icon size={designTokens.layout.navIconSize} strokeWidth={1.8} />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography noWrap sx={{ fontWeight: 700 }}>{item.issueNo}</Typography>
        <Typography color="text.secondary" noWrap variant="caption">
          {item.title ? `${item.title} · ` : ""}{triggerLabels[item.triggerType] ?? item.triggerType} · {item.occurrenceCount} görülme
        </Typography>
      </Box>
      <RowBadgeCells item={item} />
      <Box sx={{ display: { xs: "none", lg: "block" }, minWidth: 0 }}>
        <ScopeLink item={item} />
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" } }}>
        <Typography variant="body2">{formatDate(item.updatedAt)}</Typography>
        <Typography color="text.secondary" variant="caption">
          Son görülme: {formatDate(item.lastSeenAt)}
        </Typography>
      </Box>
      <Box
        sx={{
          gridColumn: { xs: "2", md: "3", lg: "auto" },
          justifySelf: { md: "end", lg: "start" },
        }}
      >
        {hasActions ? (
          <IssueActionMenu
            item={item}
            mutationPending={mutationPending}
            onAction={(action) => onAction(action, item)}
          />
        ) : (
          <Typography
            aria-label="Kullanılabilir eylem yok"
            color="text.secondary"
            sx={{ display: { xs: "none", lg: "block" } }}
            variant="body2"
          >
            —
          </Typography>
        )}
      </Box>
    </Box>
  );
}
