import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Skeleton,
  TextField,
  Typography,
} from "@mui/material";
import { Database, FileSpreadsheet, Search, type LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens } from "../theme/tokens";
import type { CatalogDataset, CatalogItemStatus, CatalogPageState } from "./model";

interface CatalogPageProps {
  state?: CatalogPageState;
  items?: CatalogDataset[];
  correlationId?: string;
  onRefresh?: () => void;
}

const statusLabels: Record<CatalogItemStatus, string> = {
  ACTIVE: "Aktif",
  INACTIVE: "Pasif",
};

function datasetTone(status: CatalogItemStatus): "success" | "unknown" {
  return status === "ACTIVE" ? "success" : "unknown";
}

function sourceIcon(sourceType: string): LucideIcon {
  if (["CSV", "EXCEL"].includes(sourceType)) return FileSpreadsheet;
  return Database;
}

function StateMessage({
  state,
  correlationId,
  onRefresh,
}: {
  state: "empty" | "error" | "unauthorized";
  correlationId?: string;
  onRefresh?: () => void;
}) {
  const content = {
    empty: ["Katalog dataset bulunamadı", "Yetkili kapsamınızda katalog dataset'i yok."],
    error: [
      "Katalog yüklenemedi",
      `Teknik bir sorun oluştu. İzleme kodu: ${correlationId ?? "bulunamadı"}.`,
    ],
    unauthorized: ["Bu görünüm için yetkiniz yok", "Katalog içeriği gösterilmedi."],
  }[state];
  return (
    <Alert
      action={
        state === "error" ? (
          <Button color="inherit" onClick={onRefresh}>
            Yeniden dene
          </Button>
        ) : undefined
      }
      severity={state === "error" ? "error" : state === "unauthorized" ? "warning" : "info"}
    >
      <Typography sx={{ fontWeight: 700 }}>{content[0]}</Typography>
      <Typography variant="body2">{content[1]}</Typography>
    </Alert>
  );
}

export function CatalogPage({
  state = "normal",
  items = [],
  correlationId,
  onRefresh,
}: CatalogPageProps) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const visibleItems = useMemo(
    () =>
      items.filter((item) => {
        const matchesQuery = `${item.name} ${item.namespace} ${item.datasetType}`
          .toLocaleLowerCase("tr-TR")
          .includes(query.toLocaleLowerCase("tr-TR"));
        return matchesQuery && (statusFilter === "ALL" || item.status === statusFilter);
      }),
    [items, query, statusFilter],
  );

  return (
    <AppShell currentPage="Katalog">
      <Box
        sx={(theme) => ({
          display: "grid",
          gap: 5,
          margin: "0 auto",
          maxWidth: theme.appLayout.contentMaxWidth,
          p: { xs: 3, md: 4, lg: 6 },
          width: "100%",
        })}
      >
        <Box
          sx={{
            alignItems: { md: "center" },
            display: "flex",
            flexDirection: { xs: "column", md: "row" },
            gap: 3,
            justifyContent: "space-between",
          }}
        >
          <Box>
            <Typography component="h1" variant="h1">
              Katalog
            </Typography>
            <Typography color="text.secondary">
              Keşfedilmiş dataset ve alan envanteri
            </Typography>
          </Box>
          {state !== "unauthorized" ? (
            <Button onClick={onRefresh} variant="outlined">
              Yenile
            </Button>
          ) : null}
        </Box>

        {state !== "unauthorized" ? (
          <Paper component="section" variant="outlined" sx={{ borderRadius: 1.5, p: 4 }}>
            <Box
              aria-label="Katalog filtreleri"
              sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "2fr 1fr" } }}
            >
              <TextField
                label="Dataset ara"
                onChange={(event) => setQuery(event.target.value)}
                slotProps={{ input: { startAdornment: <Search aria-hidden="true" size={16} /> } }}
                value={query}
              />
              <FormControl>
                <InputLabel id="catalog-status-label">Durum</InputLabel>
                <Select
                  label="Durum"
                  labelId="catalog-status-label"
                  onChange={(event) => setStatusFilter(event.target.value)}
                  value={statusFilter}
                >
                  <MenuItem value="ALL">Tüm durumlar</MenuItem>
                  {Object.entries(statusLabels).map(([value, label]) => (
                    <MenuItem key={value} value={value}>
                      {label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
          </Paper>
        ) : null}

        {state === "loading" ? (
          <Box aria-busy="true" aria-label="Katalog yükleniyor">
            {Array.from({ length: 4 }, (_, index) => (
              <Skeleton height={76} key={index} />
            ))}
          </Box>
        ) : null}

        {state === "empty" || state === "error" || state === "unauthorized" ? (
          <StateMessage correlationId={correlationId} onRefresh={onRefresh} state={state} />
        ) : null}

        {state === "normal" && visibleItems.length === 0 ? (
          <StateMessage state="empty" />
        ) : null}

        {state === "normal" && visibleItems.length > 0 ? (
          <Paper component="section" variant="outlined" sx={{ borderRadius: 1.5, overflow: "hidden" }}>
            <Box
              sx={{
                alignItems: "center",
                borderBottom: 1,
                borderColor: "divider",
                display: "flex",
                justifyContent: "space-between",
                px: 4,
                py: 3,
              }}
            >
              <Typography component="h2" variant="h3">
                Dataset Envanteri
              </Typography>
              <Typography color="text.secondary" variant="body2">
                {visibleItems.length} dataset
              </Typography>
            </Box>
            <Box
              component="ul"
              sx={{ listStyle: "none", m: 0, p: 0 }}
            >
              {visibleItems.map((item) => {
                const Icon = sourceIcon(item.datasetType);
                return (
                  <Box
                    component="li"
                    key={item.id}
                    sx={{
                      alignItems: "center",
                      borderBottom: 1,
                      borderColor: "divider",
                      display: "grid",
                      gap: 3,
                      gridTemplateColumns: {
                        xs: "40px minmax(0, 1fr)",
                        md: "40px minmax(180px, 1fr) 120px 100px 100px",
                      },
                      minHeight: 76,
                      px: 4,
                      py: 3,
                      "&:last-child": { borderBottom: 0 },
                    }}
                  >
                    <Box
                      aria-hidden="true"
                      sx={(theme) => ({
                        alignItems: "center",
                        bgcolor: theme.status.infoSurface,
                        borderRadius: 1,
                        color: theme.status.info,
                        display: "flex",
                        height: 40,
                        justifyContent: "center",
                        width: 40,
                      })}
                    >
                      <Icon size={designTokens.layout.navIconSize} strokeWidth={1.8} />
                    </Box>
                    <Box sx={{ minWidth: 0 }}>
                      <Typography
                        component={Link}
                        noWrap
                        sx={{ fontWeight: 700, textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
                        to={`/catalog/datasets/${item.id}`}
                        variant="body1"
                      >
                        {item.name}
                      </Typography>
                      <Typography color="text.secondary" noWrap variant="caption">
                        {item.namespace}
                      </Typography>
                    </Box>
                    <Typography color="text.secondary" variant="body2">
                      {item.datasetType}
                    </Typography>
                    <StatusBadge
                      label={statusLabels[item.status] ?? item.status}
                      tone={datasetTone(item.status)}
                    />
                    <Typography color="text.secondary" variant="body2">
                      {item.fieldCount} alan
                    </Typography>
                  </Box>
                );
              })}
            </Box>
          </Paper>
        ) : null}
      </Box>
    </AppShell>
  );
}
