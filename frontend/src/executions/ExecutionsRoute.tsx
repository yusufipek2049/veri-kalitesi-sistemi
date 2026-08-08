import { useCallback, useEffect, useState } from "react";
import { ExecutionApiError, cancelExecution, fetchExecutions, startExecution } from "./api";
import { executionsFromApi, syntheticExecutions, type ExecutionListItem, type ExecutionState } from "./model";
import { ExecutionsPage } from "./ExecutionsPage";

const executionStates: ExecutionState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

export function ExecutionsRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as ExecutionState | null;
  const fixtureState = import.meta.env.DEV && requestedState && executionStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<ExecutionState>(fixtureState ?? "loading");
  const [items, setItems] = useState<ExecutionListItem[]>(syntheticExecutions);
  const [correlationId, setCorrelationId] = useState<string>();
  const [starting, setStarting] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const response = await fetchExecutions(signal);
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
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  // Poll for active executions (RUNNING/QUEUED) every 5 seconds
  const hasActive = items.some((item) => item.status === "RUNNING" || item.status === "QUEUED");
  useEffect(() => {
    if (!hasActive || fixtureState) return;
    const interval = setInterval(() => void load(), 5000);
    return () => clearInterval(interval);
  }, [hasActive, fixtureState, load]);

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

  return (
    <ExecutionsPage
      cancelling={cancelling}
      correlationId={correlationId}
      items={items}
      onCancel={fixtureState ? undefined : handleCancel}
      onRefresh={() => void load()}
      onStart={fixtureState ? undefined : handleStart}
      starting={starting}
      state={fixtureState ?? state}
    />
  );
}
