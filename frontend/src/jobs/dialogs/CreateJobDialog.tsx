import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Link as MuiLink,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { Link } from "react-router-dom";
import { fetchScheduleProposals } from "../api";
import {
  timelinessNatureLabels,
  type ScheduleCreatePayload,
  type ScheduleProposalApiResponse,
  type ScheduleType,
  type TimelinessNature,
} from "../model";

export interface JobDatasetOption {
  id: string;
  label: string;
  nature: TimelinessNature | null;
}

export interface JobRuleOption {
  ruleVersionId: string;
  label: string;
  datasetId: string;
}

export interface GovernanceSubmissionResult {
  ok: boolean;
  message: string;
}

interface CreateJobDialogProps {
  open: boolean;
  datasets: JobDatasetOption[];
  rules: JobRuleOption[];
  submitting: boolean;
  governanceSubmitting: boolean;
  governanceResult: GovernanceSubmissionResult | null;
  /** Bant dışı tanım governance talebine zorlanıyor (409 sonrası). */
  governanceForced: boolean;
  error: string | null;
  onClose: () => void;
  onCreate: (payload: ScheduleCreatePayload) => void;
  onSubmitGovernance: (payload: { datasetId: string; schedule: ScheduleCreatePayload }) => void;
}

const DEFAULT_TIMEZONE = "Europe/Istanbul";
const OUT_OF_BAND_REASON_CODE = "SCHEDULE.OUT_OF_BAND.REQUEST";
const WEEKDAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"];

export function CreateJobDialog({
  open,
  datasets,
  rules,
  submitting,
  governanceSubmitting,
  governanceResult,
  governanceForced,
  error,
  onClose,
  onCreate,
  onSubmitGovernance,
}: CreateJobDialogProps) {
  const [name, setName] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [ruleVersionIds, setRuleVersionIds] = useState<string[]>([]);
  const [scheduleType, setScheduleType] = useState<ScheduleType>("INTERVAL");
  const [intervalMinutes, setIntervalMinutes] = useState<string>("");
  const [localTime, setLocalTime] = useState<string>("06:00");
  const [dayOfWeek, setDayOfWeek] = useState<string>("0");
  const [dayOfMonth, setDayOfMonth] = useState<string>("1");
  const [proposals, setProposals] = useState<ScheduleProposalApiResponse | null>(null);
  const [proposalsLoading, setProposalsLoading] = useState(false);

  const selectedDataset = datasets.find((dataset) => dataset.id === datasetId);
  const nature = selectedDataset?.nature ?? null;
  const datasetRules = useMemo(
    () => rules.filter((rule) => rule.datasetId === datasetId),
    [rules, datasetId],
  );

  useEffect(() => {
    if (!open) return;
    setName("");
    setDatasetId("");
    setRuleVersionIds([]);
    setScheduleType("INTERVAL");
    setIntervalMinutes("");
    setLocalTime("06:00");
    setDayOfWeek("0");
    setDayOfMonth("1");
    setProposals(null);
  }, [open]);

  useEffect(() => {
    if (!open || !datasetId) return;
    const controller = new AbortController();
    setProposalsLoading(true);
    fetchScheduleProposals(datasetId, controller.signal)
      .then((response) => setProposals(response))
      .catch(() => {
        if (!controller.signal.aborted) setProposals(null);
      })
      .finally(() => {
        if (!controller.signal.aborted) setProposalsLoading(false);
      });
    return () => controller.abort();
  }, [open, datasetId]);

  const buildPayload = (): ScheduleCreatePayload | null => {
    if (!name.trim() || !datasetId || ruleVersionIds.length === 0) return null;
    const payload: ScheduleCreatePayload = {
      name: name.trim(),
      dataset_id: datasetId,
      schedule_type: scheduleType,
      timezone_name: DEFAULT_TIMEZONE,
      rule_version_ids: ruleVersionIds,
    };
    if (scheduleType === "INTERVAL") {
      const parsed = Number(intervalMinutes);
      if (!Number.isInteger(parsed) || parsed < 1) return null;
      payload.interval_minutes = parsed;
    } else {
      payload.local_time = localTime;
      if (scheduleType === "WEEKLY") payload.day_of_week = Number(dayOfWeek);
      if (scheduleType === "MONTHLY") payload.day_of_month = Number(dayOfMonth);
    }
    return payload;
  };

  const isWithinBand = useMemo(() => {
    if (!proposals || !nature) return false;
    const parsedInterval = Number(intervalMinutes);
    return proposals.proposals.some((proposal) => {
      if (proposal.schedule_type !== scheduleType) return false;
      if (scheduleType === "INTERVAL") return proposal.interval_minutes === parsedInterval;
      return true;
    });
  }, [proposals, nature, scheduleType, intervalMinutes]);

  const payload = buildPayload();
  const requiresGovernance = governanceForced || (nature !== null && payload !== null && !isWithinBand);

  const handleSelectProposal = (proposalType: ScheduleType, proposalInterval: number | null) => {
    setScheduleType(proposalType);
    if (proposalInterval !== null) setIntervalMinutes(String(proposalInterval));
  };

  const handleSubmit = () => {
    if (!payload) return;
    if (requiresGovernance) {
      onSubmitGovernance({ datasetId, schedule: payload });
    } else {
      onCreate(payload);
    }
  };

  const busy = submitting || governanceSubmitting;

  return (
    <Dialog fullWidth maxWidth="sm" onClose={onClose} open={open}>
      <DialogTitle>Yeni Job</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2.5, pt: "16px !important" }}>
        {error ? (
          <Alert severity="error">{error}</Alert>
        ) : null}
        {governanceResult ? (
          <Alert severity={governanceResult.ok ? "success" : "error"}>
            {governanceResult.message}
            {governanceResult.ok ? (
              <Stack component="span" sx={{ mt: 1 }}>
                <MuiLink component={Link} to="/governance">
                  Yönetişim Görevleri ekranına git
                </MuiLink>
              </Stack>
            ) : null}
          </Alert>
        ) : null}

        <TextField
          error={name !== "" && !name.trim()}
          fullWidth
          id="job-name"
          label="Job adı"
          onChange={(event) => setName(event.target.value)}
          required
          value={name}
        />
        <TextField
          fullWidth
          label="Dataset"
          onChange={(event) => {
            setDatasetId(event.target.value);
            setRuleVersionIds([]);
          }}
          required
          select
          value={datasetId}
        >
          {datasets.map((dataset) => (
            <MenuItem key={dataset.id} value={dataset.id}>
              {dataset.label}
            </MenuItem>
          ))}
        </TextField>

        {datasetId && nature === null ? (
          <Alert severity="warning">
            Bu dataset için zamanlılık niteliği atanmamış. Job tanımlamadan önce katalog
            ekranından nitelik atayın (Yakın Zamanlı / Anlık / Toplu).
          </Alert>
        ) : null}

        {datasetId && nature !== null ? (
          <Box sx={{ display: "grid", gap: 1 }}>
            <Box sx={{ alignItems: "center", display: "flex", gap: 1 }}>
              <Chip
                color={nature === "REAL_TIME" ? "success" : nature === "NEAR_TIME" ? "info" : "warning"}
                label={`Nitelik: ${timelinessNatureLabels[nature]}`}
                size="small"
              />
              {proposals?.band ? (
                <Typography color="text.secondary" variant="caption">
                  Önerilen bant: {proposals.band}
                </Typography>
              ) : null}
            </Box>
            {proposalsLoading ? (
              <Typography color="text.secondary" variant="caption">
                Öneriler yükleniyor...
              </Typography>
            ) : (
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                {(proposals?.proposals ?? []).map((proposal) => (
                  <Chip
                    key={`${proposal.schedule_type}-${proposal.interval_minutes ?? ""}`}
                    label={proposal.label}
                    onClick={() => handleSelectProposal(proposal.schedule_type, proposal.interval_minutes)}
                    size="small"
                    variant="outlined"
                  />
                ))}
              </Box>
            )}
          </Box>
        ) : null}

        <TextField
          fullWidth
          helperText={datasetId && datasetRules.length === 0 ? "Bu dataset için aktif kural sürümü bulunamadı." : undefined}
          label="Kural sürümleri"
          onChange={(event) => {
            const value = event.target.value;
            setRuleVersionIds(
              typeof value === "string" ? value.split(",").filter(Boolean) : value,
            );
          }}
          required
          select
          slotProps={{ select: { multiple: true } }}
          value={ruleVersionIds}
        >
          {datasetRules.map((rule) => (
            <MenuItem key={rule.ruleVersionId} value={rule.ruleVersionId}>
              {rule.label}
            </MenuItem>
          ))}
        </TextField>

        {datasetId && nature !== null ? (
          <Box sx={{ display: "grid", gap: 2 }}>
            <TextField
              fullWidth
              label="Tekrar tipi"
              onChange={(event) => setScheduleType(event.target.value as ScheduleType)}
              required
              select
              value={scheduleType}
            >
              <MenuItem value="INTERVAL">Aralıklı (dakika)</MenuItem>
              <MenuItem value="DAILY">Günlük</MenuItem>
              <MenuItem value="WEEKLY">Haftalık</MenuItem>
              <MenuItem value="MONTHLY">Aylık</MenuItem>
            </TextField>
            {scheduleType === "INTERVAL" ? (
              <TextField
                fullWidth
                id="job-interval-minutes"
                slotProps={{ htmlInput: { min: 1, max: 43200 } }}
                label="Aralık (dakika)"
                onChange={(event) => setIntervalMinutes(event.target.value)}
                required
                type="number"
                value={intervalMinutes}
              />
            ) : (
              <>
                <TextField
                  fullWidth
                  slotProps={{ htmlInput: { step: 60 }, inputLabel: { shrink: true } }}
                  label="Saat"
                  onChange={(event) => setLocalTime(event.target.value)}
                  required
                  type="time"
                  value={localTime}
                />
                {scheduleType === "WEEKLY" ? (
                  <TextField
                    fullWidth
                    label="Gün"
                    onChange={(event) => setDayOfWeek(event.target.value)}
                    select
                    value={dayOfWeek}
                  >
                    {WEEKDAYS.map((day, index) => (
                      <MenuItem key={day} value={String(index)}>
                        {day}
                      </MenuItem>
                    ))}
                  </TextField>
                ) : null}
                {scheduleType === "MONTHLY" ? (
                  <TextField
                    fullWidth
                    slotProps={{ htmlInput: { min: 1, max: 31 } }}
                    label="Ayın günü"
                    onChange={(event) => setDayOfMonth(event.target.value)}
                    required
                    type="number"
                    value={dayOfMonth}
                  />
                ) : null}
              </>
            )}
          </Box>
        ) : null}

        {requiresGovernance && !governanceResult ? (
          <Alert severity="warning">
            Seçilen aralık önerilen bandın dışında. Doğrudan oluşturulamaz; maker-checker
            için yönetişim onay talebi (SCHEDULE_INTERVAL_EXCEPTION) açılır.
          </Alert>
        ) : null}
      </DialogContent>
      <DialogActions>
        <Button disabled={busy} onClick={onClose}>
          {governanceResult?.ok ? "Kapat" : "Vazgeç"}
        </Button>
        {!governanceResult ? (
          <Button
            disabled={busy || payload === null || nature === null}
            onClick={handleSubmit}
            variant="contained"
          >
            {requiresGovernance
              ? governanceSubmitting
                ? "Talep gönderiliyor..."
                : "Onay Talebi Aç"
              : submitting
                ? "Oluşturuluyor..."
                : "Job Oluştur"}
          </Button>
        ) : null}
      </DialogActions>
    </Dialog>
  );
}

export { OUT_OF_BAND_REASON_CODE };
