import { useCallback, useEffect, useMemo, useState } from "react";
import { JobsApiError, createSchedule, fetchSchedules, setScheduleActive } from "./api";
import { jobsFromApi, type JobItem, type JobState } from "./model";
import { JobsPage, type JobDatasetInfo } from "./JobsPage";
import {
  CreateJobDialog,
  OUT_OF_BAND_REASON_CODE,
  type GovernanceSubmissionResult,
  type JobDatasetOption,
  type JobRuleOption,
} from "./dialogs/CreateJobDialog";
import type { ScheduleCreatePayload } from "./model";
import { fetchRules } from "../rules/api";
import { listCatalogDatasets } from "../catalog/api";
import { createGovernanceApproval, GovernanceApiError } from "../governance/api";
import { canCreateGovernanceRequest } from "../governance/GovernanceTasksRoute";
import { useDevelopmentUser } from "../development/UserContext";

const jobStates: JobState[] = ["normal", "loading", "empty", "error", "unauthorized"];

export function JobsRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as JobState | null;
  const fixtureState = import.meta.env.DEV && requestedState && jobStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<JobState>(fixtureState ?? "loading");
  const [items, setItems] = useState<JobItem[]>([]);
  const [correlationId, setCorrelationId] = useState<string>();
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [datasetOptions, setDatasetOptions] = useState<JobDatasetOption[]>([]);
  const [ruleOptions, setRuleOptions] = useState<JobRuleOption[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [governanceSubmitting, setGovernanceSubmitting] = useState(false);
  const [governanceResult, setGovernanceResult] = useState<GovernanceSubmissionResult | null>(null);
  const [governanceForced, setGovernanceForced] = useState(false);
  const [dialogError, setDialogError] = useState<string | null>(null);
  const { currentUser } = useDevelopmentUser();
  const canCreateGovernance = canCreateGovernanceRequest(currentUser?.roles);

  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const response = await fetchSchedules(signal);
      if (signal?.aborted) return;
      const mapped = jobsFromApi(response);
      setItems(mapped);
      setCorrelationId(response.correlation_id);
      setState(mapped.length ? "normal" : "empty");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof JobsApiError) {
        setCorrelationId(error.correlationId);
        setState(error.kind === "unauthorized" ? "unauthorized" : "error");
      } else setState("error");
    }
  }, [fixtureState]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  // Katalog ve kural seçenekleri: dataset niteliği ve job→dataset eşlemesi için.
  useEffect(() => {
    if (fixtureState) return;
    const controller = new AbortController();
    const loadOptions = async () => {
      const [catalogResponse, rulesResponse] = await Promise.all([
        listCatalogDatasets(undefined, controller.signal).catch(() => null),
        fetchRules(controller.signal).catch(() => null),
      ]);
      if (controller.signal.aborted) return;
      if (catalogResponse) {
        setDatasetOptions(
          catalogResponse.items.map((item) => ({
            id: item.dataset_id,
            label: `${item.namespace}.${item.name}`,
            nature: item.timeliness_nature ?? null,
          })),
        );
      }
      if (rulesResponse) {
        setRuleOptions(
          rulesResponse.items.map((item) => ({
            ruleVersionId: item.rule_version_id,
            label: `${item.name} (v${item.version_no})`,
            datasetId: item.dataset_id,
          })),
        );
      }
    };
    void loadOptions();
    return () => controller.abort();
  }, [fixtureState]);

  const datasetInfoByJob = useMemo(() => {
    const ruleToDataset = new Map<string, string>();
    for (const rule of ruleOptions) ruleToDataset.set(rule.ruleVersionId, rule.datasetId);
    const datasetById = new Map(datasetOptions.map((option) => [option.id, option]));
    const info: Record<string, JobDatasetInfo | undefined> = {};
    for (const job of items) {
      const datasetId = ruleToDataset.get(job.ruleVersionIds[0] ?? "");
      const option = datasetId ? datasetById.get(datasetId) : undefined;
      info[job.id] = option
        ? { label: option.label, nature: option.nature }
        : undefined;
    }
    return info;
  }, [items, ruleOptions, datasetOptions]);

  const handleToggleActive = useCallback(async (jobId: string, active: boolean) => {
    setTogglingId(jobId);
    try {
      await setScheduleActive(jobId, active);
      await load();
    } catch (error) {
      if (error instanceof JobsApiError) setCorrelationId(error.correlationId);
    } finally {
      setTogglingId(null);
    }
  }, [load]);

  const handleOpenDialog = useCallback(() => {
    setGovernanceResult(null);
    setGovernanceForced(false);
    setDialogError(null);
    setDialogOpen(true);
  }, []);

  const handleCreate = useCallback(async (payload: ScheduleCreatePayload) => {
    setSubmitting(true);
    setDialogError(null);
    try {
      await createSchedule(payload);
      setDialogOpen(false);
      await load();
    } catch (error) {
      if (error instanceof JobsApiError) {
        setCorrelationId(error.correlationId);
        if (error.kind === "governance_approval_required") {
          setGovernanceForced(true);
          setDialogError(null);
        } else {
          setDialogError(error.detail);
        }
      } else {
        setDialogError("Job oluşturulamadı. Lütfen tekrar deneyin.");
      }
    } finally {
      setSubmitting(false);
    }
  }, [load]);

  const handleSubmitGovernance = useCallback(async (input: {
    datasetId: string;
    schedule: ScheduleCreatePayload;
  }) => {
    if (!canCreateGovernance) {
      setDialogError(
        "Talebi yalnız DATA_STEWARD veya DATA_GOVERNANCE_SPECIALIST rolündeki kullanıcılar açabilir.",
      );
      return;
    }
    setGovernanceSubmitting(true);
    setDialogError(null);
    try {
      await createGovernanceApproval({
        request_type: "SCHEDULE_INTERVAL_EXCEPTION",
        object_id: input.datasetId,
        reason_code: OUT_OF_BAND_REASON_CODE,
        proposed_changes: { schedule: input.schedule },
      });
      setGovernanceResult({
        ok: true,
        message:
          "Bant dışı aralık için yönetişim talebi oluşturuldu. Onay ve uygulama adımları Yönetişim Görevleri ekranında izlenir.",
      });
    } catch (error) {
      setGovernanceResult({
        ok: false,
        message:
          error instanceof GovernanceApiError
            ? error.message
            : "Yönetişim talebi oluşturulamadı. Yeniden deneyin.",
      });
    } finally {
      setGovernanceSubmitting(false);
    }
  }, [canCreateGovernance]);

  return (
    <>
      <JobsPage
        correlationId={correlationId}
        datasetInfoByJob={datasetInfoByJob}
        items={items}
        onCreate={fixtureState ? undefined : handleOpenDialog}
        onRefresh={() => void load()}
        onToggleActive={fixtureState ? undefined : (jobId, active) => void handleToggleActive(jobId, active)}
        state={fixtureState ?? state}
        togglingId={togglingId}
      />
      <CreateJobDialog
        datasets={datasetOptions}
        error={dialogError}
        governanceForced={governanceForced}
        governanceResult={governanceResult}
        governanceSubmitting={governanceSubmitting}
        onClose={() => setDialogOpen(false)}
        onCreate={(payload) => void handleCreate(payload)}
        onSubmitGovernance={(input) => void handleSubmitGovernance(input)}
        open={dialogOpen}
        rules={ruleOptions}
        submitting={submitting}
      />
    </>
  );
}
