import { useCallback, useMemo, type ReactNode } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Box,
  Button,
  Stack,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { RotateCcw } from "lucide-react";
import { AppShell } from "../components/AppShell";
import type { AnalyticsPageState } from "./model";

const TAB_ROUTES = [
  { key: "rule-health", label: "Kural Sağlığı" },
  { key: "metadata-health", label: "Metadata" },
  { key: "issues", label: "Sorunlar" },
  { key: "scoring-policy", label: "Politika Etkisi" },
] as const;

interface AnalyticsShellProps {
  activeTab: string;
  state: AnalyticsPageState;
  correlationId?: string;
  children: ReactNode;
}

export function AnalyticsShell({ activeTab, state, correlationId, children }: AnalyticsShellProps) {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const startDate = searchParams.get("start_date") ?? "";
  const endDate = searchParams.get("end_date") ?? "";
  const sourceId = searchParams.get("source_id") ?? "";
  const datasetId = searchParams.get("dataset_id") ?? "";

  const tabIndex = useMemo(
    () => TAB_ROUTES.findIndex((t) => t.key === activeTab),
    [activeTab],
  );

  const handleTabChange = useCallback(
    (_: React.SyntheticEvent, newIndex: number) => {
      const target = TAB_ROUTES[newIndex];
      if (target) {
        const params = new URLSearchParams(searchParams);
        navigate(`/analytics/${target.key}?${params.toString()}`);
      }
    },
    [navigate, searchParams],
  );

  const updateFilter = useCallback(
    (key: string, value: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (value) next.set(key, value);
        else next.delete(key);
        return next;
      });
    },
    [setSearchParams],
  );

  const clearFilters = useCallback(() => {
    setSearchParams({});
  }, [setSearchParams]);

  const hasFilters = !!(startDate || endDate || sourceId || datasetId);

  if (state === "unauthorized") {
    return (
      <AppShell currentPage="Kalite Analizleri">
        <Box sx={{ p: 4, textAlign: "center" }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            Yetki yok
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Bu analitik görünümü için yetkiniz bulunmuyor.
          </Typography>
          {correlationId && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              Correlation: {correlationId}
            </Typography>
          )}
        </Box>
      </AppShell>
    );
  }

  return (
    <AppShell currentPage="Kalite Analizleri">
      <Box sx={{ overflowX: "hidden", width: "100%" }}>
        <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tabs
            value={tabIndex >= 0 ? tabIndex : 0}
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            aria-label="Kalite Analizleri sekmeler"
          >
            {TAB_ROUTES.map((tab) => (
              <Tab key={tab.key} label={tab.label} />
            ))}
          </Tabs>
        </Box>

        {/* Shared filter bar */}
        <Stack
          direction="row"
          spacing={2}
          sx={{
            alignItems: "center",
            flexWrap: "wrap",
            gap: 1,
            p: 2,
            borderBottom: 1,
            borderColor: "divider",
          }}
        >
          <TextField
            label="Başlangıç"
            type="date"
            size="small"
            value={startDate}
            onChange={(e) => updateFilter("start_date", e.target.value)}
            placeholder=" "
            slotProps={{ inputLabel: { shrink: true } }}
            sx={{ minWidth: 150 }}
          />
          <TextField
            label="Bitiş"
            type="date"
            size="small"
            value={endDate}
            onChange={(e) => updateFilter("end_date", e.target.value)}
            placeholder=" "
            slotProps={{ inputLabel: { shrink: true } }}
            sx={{ minWidth: 150 }}
          />
          <TextField
            label="Veri Kaynağı"
            size="small"
            value={sourceId}
            onChange={(e) => updateFilter("source_id", e.target.value)}
            sx={{ minWidth: 180 }}
          />
          <TextField
            label="Dataset"
            size="small"
            value={datasetId}
            onChange={(e) => updateFilter("dataset_id", e.target.value)}
            sx={{ minWidth: 180 }}
          />
          {hasFilters && (
            <Tooltip title="Filtreleri temizle">
              <Button
                startIcon={<RotateCcw size={16} />}
                onClick={clearFilters}
                size="small"
                variant="outlined"
              >
                Temizle
              </Button>
            </Tooltip>
          )}
        </Stack>

        {/* Page content */}
        <Box sx={{ p: 2 }}>{children}</Box>
      </Box>
    </AppShell>
  );
}
