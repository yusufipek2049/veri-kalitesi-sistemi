import { useCallback, useEffect, useMemo, useState } from "react";
import { ExecutionApiError, cancelExecution, fetchExecutionDetail, fetchExecutions, startExecution, type ExecutionFilterParams } from "./api";
import { executionDetailFromApi, executionsFromApi, type ExecutionDetail, type ExecutionListItem, type ExecutionState } from "./model";
import { ExecutionsPage, type ExecutionRuleOption, type ExecutionSourceOption } from "./ExecutionsPage";
import { fetchRules, createRule } from "../rules/api";
import { fetchDataSources } from "../dataSources/api";
import { listCatalogDatasets } from "../catalog/api";

const executionStates: ExecutionState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

export function ExecutionsRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as ExecutionState | null;
  const fixtureState = import.meta.env.DEV && requestedState && executionStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<ExecutionState>(fixtureState ?? "loading");
  const [items, setItems] = useState<ExecutionListItem[]>([]);
  const [correlationId, setCorrelationId] = useState<string>();
  const [starting, setStarting] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [adhocSqlLoading, setAdhocSqlLoading] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [executionDetail, setExecutionDetail] = useState<ExecutionDetail | null>(null);
  const [ruleOptions, setRuleOptions] = useState<ExecutionRuleOption[]>([]);
  const [sourceOptions, setSourceOptions] = useState<ExecutionSourceOption[]>([]);

  // Read filter params from URL
  const urlParams = new URLSearchParams(window.location.search);
  const [datasetFilter, setDatasetFilter] = useState<string | undefined>(
    urlParams.get("dataset_id") ?? undefined,
  );
  const [scheduleFilter, setScheduleFilter] = useState<string | undefined>(
    urlParams.get("schedule_id") ?? undefined,
  );

  const load = useCallback(async (signal?: AbortSignal, filters?: ExecutionFilterParams) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const response = await fetchExecutions(filters, signal);
      const nextItems = executionsFromApi(response);
      setItems(nextItems);
      setCorrelationId(response.correlation_id);
      setState(nextItems.length ? "normal" : "empty");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof ExecutionApiError) {
        setCorrelationId(error.correlationId);
        setState(error.kind === "unauthorized" ? "unauthorized" : "error");
      } else setState("error");
    }
  }, [fixtureState]);

  const currentFilters = useMemo<ExecutionFilterParams>(() => ({
    datasetId: datasetFilter,
    scheduleId: scheduleFilter,
  }), [datasetFilter, scheduleFilter]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal, currentFilters);
    return () => controller.abort();
  }, [load, currentFilters]);

  // Derive dataset and schedule filter options from loaded items
  const datasetFilterOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const item of items) {
      for (const ds of item.datasets) {
        if (ds.datasetId && !seen.has(ds.datasetId)) {
          const label = ds.name && ds.namespace
            ? `${ds.name} (${ds.namespace})`
            : ds.name || ds.datasetId;
          seen.set(ds.datasetId, label);
        }
      }
    }
    return Array.from(seen, ([value, label]) => ({ value, label })).sort((a, b) => a.label.localeCompare(b.label, "tr"));
  }, [items]);

  const scheduleFilterOptions = useMemo(() => {
    const seen = new Set<string>();
    for (const item of items) {
      if (item.scheduleId) seen.add(item.scheduleId);
    }
    return Array.from(seen).map((value) => ({ value, label: value })).sort((a, b) => a.label.localeCompare(b.label, "tr"));
  }, [items]);

  const handleFilterChange = useCallback((filters: { datasetId?: string; scheduleId?: string }) => {
    setDatasetFilter(filters.datasetId);
    setScheduleFilter(filters.scheduleId);
  }, []);

  // Poll for active executions (RUNNING/QUEUED) every 5 seconds
  const hasActive = items.some((item) => item.status === "RUNNING" || item.status === "QUEUED");
  useEffect(() => {
    if (!hasActive || fixtureState) return;
    const interval = setInterval(() => void load(), 5000);
    return () => clearInterval(interval);
  }, [hasActive, fixtureState, load]);

  // Fetch rule and data source options for the start dialog
  useEffect(() => {
    if (fixtureState) return;
    const controller = new AbortController();
    const loadOptions = async () => {
      const [rulesResponse, sourcesResponse, catalogResponse] = await Promise.all([
        fetchRules(controller.signal).catch(() => null),
        fetchDataSources(controller.signal).catch(() => null),
        listCatalogDatasets(undefined, controller.signal).catch(() => null),
      ]);
      if (controller.signal.aborted) return;
      // Dataset → source association map for rule-bound source filtering
      const datasetLookup = new Map<string, { sourceId: string; label: string }>();
      for (const ds of catalogResponse?.items ?? []) {
        datasetLookup.set(ds.dataset_id, {
          sourceId: ds.data_source_id,
          label: `${ds.namespace}.${ds.name}`,
        });
      }
      if (rulesResponse) {
        setRuleOptions(
          rulesResponse.items.map((item) => {
            const dataset = datasetLookup.get(item.dataset_id);
            return {
              ruleVersionId: item.rule_version_id,
              label: `${item.name} (v${item.version_no})`,
              datasetId: item.dataset_id,
              datasetLabel: dataset?.label,
              sourceId: dataset?.sourceId,
            };
          }),
        );
      }
      if (sourcesResponse) {
        setSourceOptions(
          sourcesResponse.items.map((item) => ({
            sourceId: item.data_source_id,
            label: item.name,
          })),
        );
      }
    };
    void loadOptions();
    return () => controller.abort();
  }, [fixtureState]);

  const handleStart = useCallback(async (ruleVersionIds: string[], sourceIds: string[], idempotencyKey: string) => {
    setStarting(true);
    try {
      await startExecution({ rule_version_ids: ruleVersionIds, source_ids: sourceIds, idempotency_key: idempotencyKey, execution_mode: "OFFICIAL" });
      await load();
    } catch (error) {
      if (error instanceof ExecutionApiError) setCorrelationId(error.correlationId);
    } finally {
      setStarting(false);
    }
  }, [load]);

  const handleAdhocSql = useCallback(async (sql: string, sourceIds: string[], timeoutSeconds: number, rowLimit: number) => {
    setAdhocSqlLoading(true);
    try {
      // Step 1: Create a CUSTOM_SQL rule with the provided SQL
      const ruleCode = `ADHOC_SQL_${Date.now()}`;
      const mutation = await createRule({
        code: ruleCode,
        name: `Ad-hoc SQL ${new Date().toLocaleString("tr-TR")}`,
        dataset_id: sourceIds[0] ?? "adhoc",
        rule_type: "CUSTOM_SQL",
        primary_dimension: "ACCURACY",
        threshold: 100,
        weight: 1,
        criticality: "MEDIUM",
        owner_user_id: "adhoc-user",
        parameters: {
          sql,
          timeout_seconds: timeoutSeconds,
          row_limit: rowLimit,
          scope_type: "DATASET",
          query_reference: `adhoc.${ruleCode}`,
        },
      });
      // Step 2: Start execution with the created rule version
      await startExecution({
        rule_version_ids: [mutation.item.rule_version_id],
        source_ids: sourceIds,
        idempotency_key: crypto.randomUUID(),
        execution_mode: "OFFICIAL",
      });
      await load();
    } catch (error) {
      if (error instanceof ExecutionApiError) setCorrelationId(error.correlationId);
      throw error;
    } finally {
      setAdhocSqlLoading(false);
    }
  }, [load]);

  const handleCancel = useCallback(async (executionId: string, reason: string) => {
    setCancelling(true);
    try {
      await cancelExecution(executionId, { reason });
      await load();
    } catch (error) {
      if (error instanceof ExecutionApiError) setCorrelationId(error.correlationId);
    } finally {
      setCancelling(false);
    }
  }, [load]);

  const handleSelect = useCallback(async (executionId: string) => {
    setDetailOpen(true);
    setDetailLoading(true);
    setExecutionDetail(null);
    try {
      const response = await fetchExecutionDetail(executionId);
      setExecutionDetail(executionDetailFromApi(response));
    } catch {
      setExecutionDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const handleCloseDetail = useCallback(() => {
    setDetailOpen(false);
    setExecutionDetail(null);
  }, []);

  return (
    <ExecutionsPage
      cancelling={cancelling}
      adhocSqlLoading={adhocSqlLoading}
      correlationId={correlationId}
      detailOpen={detailOpen}
      executionDetail={executionDetail}
      detailLoading={detailLoading}
      items={items}
      onCancel={fixtureState ? undefined : handleCancel}
      onAdhocSql={fixtureState ? undefined : handleAdhocSql}
      onCloseDetail={handleCloseDetail}
      onFilterChange={fixtureState ? undefined : handleFilterChange}
      onRefresh={() => void load(undefined, currentFilters)}
      onSelect={fixtureState ? undefined : handleSelect}
      onStart={fixtureState ? undefined : handleStart}
      activeDatasetFilter={datasetFilter}
      activeScheduleFilter={scheduleFilter}
      datasetFilterOptions={datasetFilterOptions}
      ruleOptions={ruleOptions}
      scheduleFilterOptions={scheduleFilterOptions}
      sourceOptions={sourceOptions}
      starting={starting}
      state={fixtureState ?? state}
    />
  );
}
