import { createTheme } from "@mui/material/styles";
import { designTokens } from "./tokens";

declare module "@mui/material/styles" {
  interface Theme {
    status: Record<keyof typeof designTokens.color.status, string>;
    appLayout: typeof designTokens.layout;
  }

  interface ThemeOptions {
    status?: Record<keyof typeof designTokens.color.status, string>;
    appLayout?: typeof designTokens.layout;
  }
}

export const appTheme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: designTokens.color.brand.primary,
      dark: designTokens.color.brand.primaryHover,
      contrastText: designTokens.color.brand.onPrimary,
    },
    background: {
      default: designTokens.color.canvas,
      paper: designTokens.color.surface,
    },
    text: {
      primary: designTokens.color.text.primary,
      secondary: designTokens.color.text.muted,
    },
    divider: designTokens.color.border,
  },
  status: designTokens.color.status,
  appLayout: designTokens.layout,
  spacing: 4,
  shape: {
    borderRadius: designTokens.radius.control,
  },
  typography: {
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
    fontSize: 14,
    h1: { fontSize: 28, lineHeight: 1.2, fontWeight: 700, letterSpacing: 0 },
    h2: { fontSize: 20, lineHeight: 1.3, fontWeight: 700, letterSpacing: 0 },
    h3: { fontSize: 16, lineHeight: 1.35, fontWeight: 700, letterSpacing: 0 },
    body1: { fontSize: 14, lineHeight: 1.5, letterSpacing: 0 },
    body2: { fontSize: 12, lineHeight: 1.45, letterSpacing: 0 },
    button: { fontSize: 14, fontWeight: 700, letterSpacing: 0, textTransform: "none" },
    caption: { fontSize: 12, lineHeight: 1.4, letterSpacing: 0 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        "*, *::before, *::after": { boxSizing: "border-box" },
        html: { minWidth: 0, backgroundColor: designTokens.color.canvas },
        body: { margin: 0, minWidth: 0, backgroundColor: designTokens.color.canvas },
        "#root": { minHeight: "100vh" },
        "*:focus-visible": {
          outline: `3px solid ${designTokens.color.brand.primary}`,
          outlineOffset: 2,
        },
        "@media (prefers-reduced-motion: reduce)": {
          "*, *::before, *::after": {
            animationDuration: "0.01ms !important",
            transitionDuration: "0.01ms !important",
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
        },
      },
    },
    MuiButton: {
      defaultProps: {
        disableElevation: true,
      },
    },
    MuiButtonBase: {
      styleOverrides: {
        root: {
          "&:focus-visible": {
            outline: `3px solid ${designTokens.color.brand.primary}`,
            outlineOffset: 2,
          },
        },
      },
    },
  },
});
