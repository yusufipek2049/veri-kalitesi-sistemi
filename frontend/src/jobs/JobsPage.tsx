import {
  Alert,
  Box,
  Button,
  Chip,
  Paper,
  Skeleton,
  Typography,
} from "@mui/material";
import { CalendarClock, Plus, RefreshCw } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import {
  scheduleSummary,
  timelinessNatureLabels,
  type JobItem,
  type JobState,
  type TimelinessNature,
} from "./model";

export interface JobDatasetInfo {
  label: string;
  nature: TimelinessNature | null;
}

interface JobsPageProps {
  state?: JobState;
  items: JobItem[];
  correlationId?: string;
  /** job id → ilişkili dataset bilgisi (kurallardan türetilir). */
  datasetInfoByJob: Record<string, JobDatasetInfo | undefined>;
  togglingId?: string | null;
  onRefresh?: () => void;
  onToggleActive?: (jobId: string, active: boolean) => void;
  onCreate?: () => void;
}

const natureTone = (nature: TimelinessNature | null): "info" | "success" | "warning" | "default" => {
  switch (nature) {
    case "REAL_TIME":
      return "success";
    case "NEAR_TIME":
      return "info";
    case "BATCH_TIME":
      return "warning";
    default:
      return "default";
  }
};

const jobColumns = ["Job", "Dataset", "Aralık", "Nitelik", "Sonraki çalıştırma", "Durum"];

const jobGridSx = {
  display: "grid",
  gap: 2,
  gridTemplateColumns: {
    xs: "minmax(0, 1fr)",
    md: "minmax(180px, 1.4fr) minmax(140px, 1fr) minmax(140px, 1fr) 130px 160px 110px 130px",
  },
  px: 4,
} as const;

function formatRunAt(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function JobsPage({
  state = "normal",
  items,
  correlationId,
  datasetInfoByJob,
  togglingId = null,
  onRefresh,
  onToggleActive,
  onCreate,
}: JobsPageProps) {
  return (
    <AppShell currentPage="Jobs">
      <Box
        sx={(theme) => ({
          display: "grid",
          gap: 4,
          margin: "0 auto",
          maxWidth: theme.appLayout.contentMaxWidth,
          p: { xs: 3, md: 4, lg: 6 },
          width: "100%",
        })}
      >
        <Box
          sx={{
            alignItems: "center",
            display: "flex",
            flexDirection: { xs: "column", md: "row" },
            gap: 2,
            justifyContent: "space-between",
          }}
        >
          <Box sx={{ alignItems: "center", display: "flex", gap: 1.5 }}>
            <CalendarClock aria-hidden="true" size={24} />
            <Typography component="h1" variant="h1">
              Jobs
            </Typography>
          </Box>
          <Box sx={{ display: "flex", gap: 2 }}>
            {onCreate ? (
              <Button
                onClick={onCreate}
                startIcon={<Plus aria-hidden="true" size={16} />}
                variant="contained"
              >
                Yeni Job
              </Button>
            ) : null}
            <Button
              onClick={onRefresh}
              startIcon={<RefreshCw aria-hidden="true" size={16} />}
              variant="outlined"
            >
              Yenile
            </Button>
          </Box>
        </Box>

        {state === "loading" ? (
          <Box aria-busy="true">
            <Skeleton height={48} />
            <Skeleton height={220} sx={{ mt: 2 }} />
          </Box>
        ) : null}

        {state === "error" ? (
          <Alert severity="error">
            <Typography sx={{ fontWeight: 700 }}>Job listesi yüklenemedi</Typography>
            <Typography variant="body2">İzleme kodu: {correlationId ?? "bulunamadı"}.</Typography>
          </Alert>
        ) : null}

        {state === "unauthorized" ? (
          <Alert severity="warning">
            <Typography sx={{ fontWeight: 700 }}>Bu görünüm için yetkiniz yok</Typography>
            <Typography variant="body2">Job listesi gösterilmedi.</Typography>
          </Alert>
        ) : null}

        {state === "empty" ? (
          <Alert severity="info">
            <Typography variant="body2">
              Henüz tanımlı job yok. Tablo niteliğine uygun ilk zamanlayıcıyı oluşturun.
            </Typography>
          </Alert>
        ) : null}

        {state === "normal" ? (
          <Paper variant="outlined" sx={{ borderRadius: 1.5, overflow: "hidden" }}>
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
                Zamanlayıcılar
              </Typography>
              <Typography color="text.secondary" variant="body2">
                {items.length} job
              </Typography>
            </Box>
            {items.length > 0 ? (
              <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
                <Box
                  component="li"
                  sx={{
                    ...jobGridSx,
                    alignItems: "center",
                    bgcolor: "action.hover",
                    borderBottom: 1,
                    borderColor: "divider",
                    display: { xs: "none", md: "grid" },
                    py: 1.5,
                  }}
                >
                  {[...jobColumns, "Aksiyon"].map((column) => (
                    <Typography
                      color="text.secondary"
                      key={column}
                      sx={{ fontWeight: 700 }}
                      variant="caption"
                    >
                      {column}
                    </Typography>
                  ))}
                </Box>
                {items.map((job) => {
                  const info = datasetInfoByJob[job.id];
                  const nature = info?.nature ?? null;
                  return (
                    <Box
                      component="li"
                      key={job.id}
                      sx={{
                        ...jobGridSx,
                        alignItems: "center",
                        borderBottom: 1,
                        borderColor: "divider",
                        minHeight: 60,
                        py: 2,
                        "&:last-child": { borderBottom: 0 },
                      }}
                    >
                      <Box sx={{ minWidth: 0 }}>
                        <Typography noWrap sx={{ fontWeight: 600 }} variant="body2">
                          {job.name}
                        </Typography>
                        <Typography color="text.secondary" noWrap variant="caption">
                          {job.ruleVersionIds.length} kural · {job.timezoneName}
                        </Typography>
                      </Box>
                      <Typography color="text.secondary" variant="body2">
                        {info?.label ?? "—"}
                      </Typography>
                      <Typography color="text.secondary" variant="body2">
                        {scheduleSummary(job)}
                      </Typography>
                      <Box sx={{ alignItems: "center", display: "flex" }}>
                        <Chip
                          color={natureTone(nature)}
                          label={nature ? timelinessNatureLabels[nature] : "Nitelik yok"}
                          size="small"
                          variant="outlined"
                        />
                      </Box>
                      <Typography color="text.secondary" variant="body2">
                        {formatRunAt(job.nextRunAt)}
                      </Typography>
                      <Box sx={{ alignItems: "center", display: "flex" }}>
                        <StatusBadge
                          label={job.isActive ? "AKTİF" : "PASİF"}
                          tone={job.isActive ? "success" : "unknown"}
                        />
                      </Box>
                      <Box>
                        {onToggleActive ? (
                          <Button
                            disabled={togglingId === job.id}
                            onClick={() => onToggleActive(job.id, !job.isActive)}
                            size="small"
                            variant="outlined"
                          >
                            {job.isActive ? "Pasifleştir" : "Aktifleştir"}
                          </Button>
                        ) : null}
                      </Box>
                    </Box>
                  );
                })}
              </Box>
            ) : (
              <Box sx={{ p: 4 }}>
                <Alert severity="info">
                  <Typography variant="body2">Gösterilecek job bulunamadı.</Typography>
                </Alert>
              </Box>
            )}
          </Paper>
        ) : null}
      </Box>
    </AppShell>
  );
}
