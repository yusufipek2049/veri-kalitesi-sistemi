import { useCallback, useEffect, useState } from "react";
import {
  RuleApiError,
  createRule,
  createRuleVersion,
  decideRuleApproval,
  fetchRuleDetail,
  fetchRules,
  passivateRule,
  requestRuleApproval,
  testRule,
  withdrawRuleApproval,
  activateRule,
} from "./api";
import { ruleFromApi, rulesFromApi, type RuleCreateRequest, type RuleListItem, type RuleState, type RuleTestResult, type RuleVersionCreateRequest } from "./model";
import { RulesPage } from "./RulesPage";
import { listCatalogDatasets, listCatalogFields } from "../catalog/api";

const ruleStates: RuleState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

export function RulesRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as RuleState | null;
  const fixtureState = import.meta.env.DEV && requestedState && ruleStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<RuleState>(fixtureState ?? "loading");
  const [items, setItems] = useState<RuleListItem[]>([]);
  const [correlationId, setCorrelationId] = useState<string>();
  const [catalogDatasets, setCatalogDatasets] = useState<{ id: string; name: string; namespace: string }[]>([]);
  const [catalogFields, setCatalogFields] = useState<{ id: string; name: string; datasetId: string }[]>([]);
  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const [response, catalogResponse] = await Promise.all([
        fetchRules(signal),
        listCatalogDatasets(undefined),
      ]);
      const nextItems = rulesFromApi(response);
      setItems(nextItems);
      setCorrelationId(response.correlation_id);
      setCatalogDatasets(
        catalogResponse.items.map((ds) => ({
          id: ds.dataset_id,
          name: ds.name,
          namespace: ds.namespace,
        })),
      );
      setState(nextItems.length ? "normal" : "empty");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof RuleApiError) {
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

  const handleCreateRule = useCallback(async (payload: RuleCreateRequest) => {
    const response = await createRule(payload);
    const updated = ruleFromApi(response);
    setItems((current) => [...current, updated]);
    setCorrelationId(response.correlation_id);
  }, []);

  const handleCreateVersion = useCallback(
    async (item: RuleListItem, data: RuleVersionCreateRequest) => {
      const response = await createRuleVersion(item.id, data);
      const updated = ruleFromApi(response);
      setItems((current) => current.map((candidate) =>
        candidate.id === updated.id ? updated : candidate,
      ));
      setCorrelationId(response.correlation_id);
    },
    [],
  );

  const handleTestRule = useCallback(
    async (item: RuleListItem, ruleVersionId: string): Promise<RuleTestResult> => {
      const result = await testRule(item.id, { rule_version_id: ruleVersionId, limit: 10000 });
      setCorrelationId(result.rule_test_result_id);
      return result;
    },
    [],
  );

  const handleActivateRule = useCallback(async (item: RuleListItem) => {
    const response = await activateRule(item.id);
    const updated = ruleFromApi(response);
    setItems((current) => current.map((candidate) =>
      candidate.id === updated.id ? updated : candidate,
    ));
    setCorrelationId(response.correlation_id);
  }, []);

  const handleRequestApproval = useCallback(async (item: RuleListItem) => {
    const response = await requestRuleApproval(item.id);
    const updated = ruleFromApi(response);
    setItems((current) => current.map((candidate) =>
      candidate.id === updated.id ? updated : candidate,
    ));
    setCorrelationId(response.correlation_id);
  }, []);

  const handleDecideApproval = useCallback(
    async (item: RuleListItem, approvalRequestId: string, decision: "APPROVE" | "REJECT", reasonCode: string) => {
      const response = await decideRuleApproval(approvalRequestId, { approval_request_id: approvalRequestId, decision, reason_code: reasonCode });
      const updated = ruleFromApi(response);
      setItems((current) => current.map((candidate) =>
        candidate.id === updated.id ? updated : candidate,
      ));
      setCorrelationId(response.correlation_id);
    },
    [],
  );

  const handleWithdrawApproval = useCallback(
    async (item: RuleListItem, approvalRequestId: string, reasonCode: string) => {
      const response = await withdrawRuleApproval(approvalRequestId, { approval_request_id: approvalRequestId, reason_code: reasonCode });
      const updated = ruleFromApi(response);
      setItems((current) => current.map((candidate) =>
        candidate.id === updated.id ? updated : candidate,
      ));
      setCorrelationId(response.correlation_id);
    },
    [],
  );

  const handlePassivateRule = useCallback(async (item: RuleListItem) => {
    const response = await passivateRule(item.id);
    const updated = ruleFromApi(response);
    setItems((current) => current.map((candidate) =>
      candidate.id === updated.id ? updated : candidate,
    ));
    setCorrelationId(response.correlation_id);
  }, []);

  const handleLoadFields = useCallback(async (datasetId: string) => {
    try {
      const response = await listCatalogFields(datasetId);
      setCatalogFields((prev) => {
        // Merge, avoiding duplicates from different dataset loads
        const existing = new Set(prev.map((f) => f.id));
        const newFields = response.items
          .map((f) => ({ id: f.data_field_id, name: f.name, datasetId: f.dataset_id }))
          .filter((f) => !existing.has(f.id));
        return [...prev, ...newFields];
      });
    } catch {
      // Field loading failure is non-fatal
    }
  }, []);

  const handleLoadRuleDetail = useCallback(async (ruleId: string): Promise<Record<string, unknown>> => {
    const response = await fetchRuleDetail(ruleId);
    return response.definition;
  }, []);

  return (
    <RulesPage
      catalogDatasets={catalogDatasets}
      catalogFields={catalogFields}
      correlationId={correlationId}
      items={items}
      onRefresh={() => void load()}
      state={fixtureState ?? state}
      onCreateRule={handleCreateRule}
      onCreateVersion={handleCreateVersion}
      onTestRule={handleTestRule}
      onActivateRule={handleActivateRule}
      onRequestApproval={handleRequestApproval}
      onDecideApproval={handleDecideApproval}
      onWithdrawApproval={handleWithdrawApproval}
      onPassivateRule={handlePassivateRule}
      onLoadFields={handleLoadFields}
      onLoadRuleDetail={handleLoadRuleDetail}
    />
  );
}
