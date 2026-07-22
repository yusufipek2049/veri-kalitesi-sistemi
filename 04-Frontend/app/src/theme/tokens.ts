const sharedColorTokens = {
  brand: {
    primary: "#FDB813",
    primaryHover: "#E5A500",
    onPrimary: "#172033",
  },
  nav: {
    background: "#0B1F3A",
    hover: "#142D4F",
    text: "#DCE6F3",
    muted: "#91A4BC",
  },
} as const;

export const colorModeTokens = {
  light: {
    ...sharedColorTokens,
    canvas: "#F3F5F7",
    surface: "#FFFFFF",
    surfaceMuted: "#F8FAFC",
    text: {
      primary: "#172033",
      muted: "#5B6574",
    },
    border: "#D8DEE7",
    status: {
      critical: "#C62828",
      criticalSurface: "#FDECEC",
      technical: "#7B1FA2",
      technicalSurface: "#F5E9FA",
      warning: "#C75B00",
      warningSurface: "#FFF1E5",
      success: "#2E7D32",
      successSurface: "#EAF5EA",
      info: "#1565C0",
      infoSurface: "#EAF2FC",
      unknown: "#667085",
      unknownSurface: "#EEF1F5",
    },
  },
  dark: {
    ...sharedColorTokens,
    canvas: "#111418",
    surface: "#1A1F26",
    surfaceMuted: "#222832",
    text: {
      primary: "#F5F7FA",
      muted: "#B5BDC9",
    },
    border: "#353D49",
    status: {
      critical: "#FF8A8A",
      criticalSurface: "#3B2025",
      technical: "#D8A1E3",
      technicalSurface: "#35223C",
      warning: "#FFB96A",
      warningSurface: "#3B2A18",
      success: "#89D18F",
      successSurface: "#1D3523",
      info: "#78BDF2",
      infoSurface: "#1C3042",
      unknown: "#C1C9D4",
      unknownSurface: "#2A3039",
    },
  },
} as const;

export const designTokens = {
  color: {
    ...colorModeTokens.light,
  },
  radius: {
    control: 4,
    surface: 6,
    modal: 8,
  },
  shadow: {
    surface: "0 1px 2px rgba(23, 32, 51, 0.08)",
    overlay: "0 8px 24px rgba(23, 32, 51, 0.18)",
  },
  layout: {
    navExpanded: 216,
    navCompact: 72,
    navItemHeight: 40,
    navIconSize: 18,
    navIconSlot: 24,
    brandMarkSize: 32,
    topBarHeight: 56,
    contentMaxWidth: 1680,
    chartHeight: 300,
    kpiMinHeight: 116,
    tableMaxHeight: 312,
  },
  motion: {
    short: "160ms",
  },
} as const;

export type StatusTone =
  | "critical"
  | "technical"
  | "warning"
  | "success"
  | "info"
  | "unknown";

export type AppColorMode = keyof typeof colorModeTokens;
