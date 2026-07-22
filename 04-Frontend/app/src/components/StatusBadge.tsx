import { Box } from "@mui/material";
import type { StatusTone } from "../theme/tokens";

const toneGlyph: Record<StatusTone, string> = {
  critical: "!",
  technical: "×",
  warning: "!",
  success: "✓",
  info: "i",
  unknown: "—",
};

const surfaceKey: Record<StatusTone, "criticalSurface" | "technicalSurface" | "warningSurface" | "successSurface" | "infoSurface" | "unknownSurface"> = {
  critical: "criticalSurface",
  technical: "technicalSurface",
  warning: "warningSurface",
  success: "successSurface",
  info: "infoSurface",
  unknown: "unknownSurface",
};

interface StatusBadgeProps {
  label: string;
  tone: StatusTone;
}

export function StatusBadge({ label, tone }: StatusBadgeProps) {
  return (
    <Box
      component="span"
      aria-label={`Durum: ${label}`}
      sx={(theme) => ({
        alignItems: "center",
        bgcolor: theme.status[surfaceKey[tone]],
        borderRadius: theme.shape.borderRadius,
        color: theme.status[tone],
        display: "inline-flex",
        fontSize: theme.typography.caption.fontSize,
        fontWeight: 700,
        gap: 1,
        lineHeight: 1,
        maxWidth: "100%",
        px: 2,
        py: 1.5,
      })}
    >
      <Box component="span" aria-hidden="true" sx={{ fontWeight: 800 }}>
        {toneGlyph[tone]}
      </Box>
      <Box component="span" sx={{ overflowWrap: "anywhere" }}>
        {label}
      </Box>
    </Box>
  );
}
