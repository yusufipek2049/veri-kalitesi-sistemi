import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { createAppTheme } from "./theme";
import type { AppColorMode } from "./tokens";

const THEME_STORAGE_KEY = "veri-kalitesi-theme";

interface ThemeModeContextValue {
  mode: AppColorMode;
  toggleMode: () => void;
}

const ThemeModeContext = createContext<ThemeModeContextValue | null>(null);

interface ThemeModeProviderProps {
  children: ReactNode;
  forcedMode?: AppColorMode;
}

function readStoredMode(): AppColorMode {
  try {
    const storedMode = window.localStorage.getItem(THEME_STORAGE_KEY);
    return storedMode === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function ThemeModeProvider({ children, forcedMode }: ThemeModeProviderProps) {
  const [selectedMode, setSelectedMode] = useState<AppColorMode>(readStoredMode);
  const mode = forcedMode ?? selectedMode;
  const theme = useMemo(() => createAppTheme(mode), [mode]);

  useEffect(() => {
    document.documentElement.dataset.theme = mode;
  }, [mode]);

  const value = useMemo<ThemeModeContextValue>(() => ({
    mode,
    toggleMode: () => {
      if (forcedMode) return;
      setSelectedMode((currentMode) => {
        const nextMode = currentMode === "light" ? "dark" : "light";
        try {
          window.localStorage.setItem(THEME_STORAGE_KEY, nextMode);
        } catch {
          // Tema tercihi kalıcılaştırılamasa da oturum içindeki seçim korunur.
        }
        return nextMode;
      });
    },
  }), [forcedMode, mode]);

  return (
    <ThemeModeContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeModeContext.Provider>
  );
}

export function useThemeMode(): ThemeModeContextValue {
  const context = useContext(ThemeModeContext);
  if (!context) throw new Error("useThemeMode must be used within ThemeModeProvider.");
  return context;
}
