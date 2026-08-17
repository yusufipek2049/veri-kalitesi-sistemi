import { useMemo } from "react";
import {
  Box,
  IconButton,
  Paper,
  Tooltip,
  Typography,
} from "@mui/material";
import { Copy } from "lucide-react";
import { StatusBadge } from "../components/StatusBadge";
import type { StatusTone } from "../theme/tokens";
import type { AuditEventListItem } from "./model";

interface AuditTimelineProps {
  items: AuditEventListItem[];
  onSelect: (item: AuditEventListItem) => void;
  /** Aktör kimliğini demo kullanıcı adına çevirir; eşleşme yoksa undefined. */
  actorLabel?: (actorId: string) => string | undefined;
}

const groupColors = [
  "#2563eb",
  "#7c3aed",
  "#db2777",
  "#dc2626",
  "#ea580c",
  "#ca8a04",
  "#16a34a",
  "#0891b2",
  "#4f46e5",
  "#9333ea",
];

const resultLabels: Record<string, string> = {
  SUCCESS: "Başarılı",
  FAILURE: "Başarısız",
  DENIED: "Reddedildi",
};

function resultTone(result: string): StatusTone {
  if (result === "SUCCESS") return "success";
  if (result === "DENIED") return "warning";
  return "technical";
}

function colorForCorrelation(correlationId: string): string {
  let hash = 0;
  for (const character of correlationId) {
    hash = ((hash << 5) - hash + character.charCodeAt(0)) | 0;
  }
  return groupColors[Math.abs(hash) % groupColors.length];
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AuditTimeline({ actorLabel, items, onSelect }: AuditTimelineProps) {
  const groups = useMemo(() => {
    const grouped = new Map<string, AuditEventListItem[]>();
    for (const item of items) {
      const group = grouped.get(item.correlationId) ?? [];
      group.push(item);
      grouped.set(item.correlationId, group);
    }
    return [...grouped.entries()]
      .map(([correlationId, events]) => ({
        color: colorForCorrelation(correlationId),
        correlationId,
        events: events.sort((left, right) => (
          new Date(left.occurredAt).getTime() - new Date(right.occurredAt).getTime()
          || left.sequenceNo - right.sequenceNo
        )),
      }))
      .sort((left, right) => (
        new Date(left.events[0].occurredAt).getTime()
        - new Date(right.events[0].occurredAt).getTime()
      ));
  }, [items]);

  return (
    <Box aria-label="Audit olayları zaman çizelgesi" sx={{ display: "grid", gap: 4 }}>
      {groups.map((group) => (
        <Box
          component="section"
          data-group-color={group.color}
          key={group.correlationId}
          sx={{ display: "grid", gap: 2 }}
        >
          <Box sx={{ alignItems: "center", display: "flex", gap: 1 }}>
            <Box aria-hidden="true" sx={{ bgcolor: group.color, borderRadius: "50%", height: 10, width: 10 }} />
            <Typography component="h3" sx={{ fontFamily: "monospace", fontWeight: 700, wordBreak: "break-all" }} variant="body2">
              {group.correlationId}
            </Typography>
            <Tooltip title="İlişki kodunu kopyala">
              <IconButton
                aria-label={`${group.correlationId} ilişki kodunu kopyala`}
                onClick={() => void navigator.clipboard.writeText(group.correlationId)}
                size="small"
              >
                <Copy aria-hidden="true" size={14} />
              </IconButton>
            </Tooltip>
          </Box>
          <Box sx={{ borderLeft: `2px solid ${group.color}`, display: "grid", gap: 2, ml: 0.5, pl: 3 }}>
            {group.events.map((item) => (
              <Paper
                component="button"
                data-event-id={item.eventId}
                key={item.eventId}
                onClick={() => onSelect(item)}
                sx={{
                  bgcolor: "background.paper",
                  borderColor: group.color,
                  borderRadius: 1.5,
                  cursor: "pointer",
                  display: "grid",
                  gap: 1,
                  justifyItems: "start",
                  maxWidth: 560,
                  p: 3,
                  position: "relative",
                  textAlign: "left",
                  width: "100%",
                  "&::before": {
                    bgcolor: group.color,
                    borderRadius: "50%",
                    content: '""',
                    height: 10,
                    left: -30,
                    position: "absolute",
                    top: 24,
                    width: 10,
                  },
                  "&:hover": { bgcolor: "action.hover" },
                }}
                variant="outlined"
              >
                <Box sx={{ alignItems: "center", display: "flex", gap: 2, justifyContent: "space-between", width: "100%" }}>
                  <Typography sx={{ fontWeight: 700 }} variant="body2">{item.action}</Typography>
                  <StatusBadge label={resultLabels[item.result] ?? item.result} tone={resultTone(item.result)} />
                </Box>
                <Typography color="text.secondary" variant="body2">{actorLabel?.(item.actorId) ?? item.actorId}</Typography>
                <Typography color="text.secondary" variant="caption">{formatDate(item.occurredAt)}</Typography>
              </Paper>
            ))}
          </Box>
        </Box>
      ))}
    </Box>
  );
}
