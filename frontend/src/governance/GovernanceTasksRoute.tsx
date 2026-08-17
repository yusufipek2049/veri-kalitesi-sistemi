import { useCallback, useEffect, useState } from "react";
import {
  GovernanceApiError,
  applyGovernanceApproval,
  createGovernanceApproval,
  decideGovernanceApproval,
  fetchGovernanceApprovals,
  withdrawGovernanceApproval,
} from "./api";
import {
  governanceItemsFromApi,
  type GovernanceApprovalItem,
  type GovernanceState,
  type GovernanceView,
} from "./model";
import { GovernanceTasksPage } from "./GovernanceTasksPage";
import { listCatalogDatasets, listCatalogFields } from "../catalog/api";
import { fetchRules } from "../rules/api";
import { fetchExecutions } from "../executions/api";
import { useDevelopmentUser } from "../development/UserContext";

const governanceStates: GovernanceState[] = ["normal", "loading", "empty", "error", "unauthorized"];

interface GovernanceDatasetOption {
  id: string;
  name: string;
  namespace: string;
  ownerId: string | null;
}

const governanceMakerRoles = new Set(["DATA_STEWARD", "DATA_GOVERNANCE_SPECIALIST"]);

export function canCreateGovernanceRequest(roles: string | undefined): boolean {
  return (roles?.split(/\s*\/\s*/) ?? []).some((role) => governanceMakerRoles.has(role));
}

export function GovernanceTasksRoute() {
  const { availableUsers, currentUser } = useDevelopmentUser();
  const canCreateRequest = canCreateGovernanceRequest(currentUser?.roles);
  const requestedState = new URLSearchParams(window.location.search).get("state") as GovernanceState | null;
  const fixtureState = import.meta.env.DEV && requestedState && governanceStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<GovernanceState>(fixtureState ?? "loading");
  const [view, setView] = useState<GovernanceView>("PENDING");
  const [items, setItems] = useState<GovernanceApprovalItem[]>([]);
  const [datasets, setDatasets] = useState<GovernanceDatasetOption[]>([]);
  const [ruleOptions, setRuleOptions] = useState<{ ruleVersionId: string; label: string }[]>([]);
  const [executionOptions, setExecutionOptions] = useState<{ executionId: string; label: string }[]>(
    [],
  );
  const [correlationId, setCorrelationId] = useState<string>();
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(
    async (nextView: GovernanceView, signal?: AbortSignal) => {
      if (fixtureState) return;
      setState("loading");
      try {
        const [response, catalogResponse] = await Promise.all([
          fetchGovernanceApprovals(nextView, signal),
          listCatalogDatasets(undefined, signal).catch(() => null),
          fetchRules(signal)
            .then((rulesResponse) => {
              setRuleOptions(
                rulesResponse.items.map((item) => ({
                  ruleVersionId: item.rule_version_id,
                  label: `${item.name} (v${item.version_no})`,
                })),
              );
            })
            .catch(() => null),
          fetchExecutions(signal)
            .then((executionsResponse) => {
              setExecutionOptions(
                executionsResponse.items.map((item) => ({
                  executionId: item.execution_id,
                  label: `${item.execution_id.slice(0, 12)}… · ${item.status} · ${item.rule_count} kural`,
                })),
              );
            })
            .catch(() => null),
        ]);
        if (signal?.aborted) return;
        const mapped = governanceItemsFromApi(response);
        setItems(mapped);
        setCorrelationId(response.correlation_id);
        if (catalogResponse) {
          setDatasets(
            catalogResponse.items.map((dataset) => ({
              id: dataset.dataset_id,
              name: dataset.name,
              namespace: dataset.namespace,
              ownerId: dataset.owner_user_id ?? null,
            })),
          );
        }
        setState(mapped.length ? "normal" : "empty");
      } catch (error) {
        if (signal?.aborted) return;
        if (error instanceof GovernanceApiError) {
          setCorrelationId(error.correlationId);
          setState(error.kind === "unauthorized" ? "unauthorized" : "error");
        } else {
          setState("error");
        }
      }
    },
    [fixtureState],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(view, controller.signal);
    return () => controller.abort();
  }, [load, view]);

  const handleViewChange = useCallback((nextView: GovernanceView) => {
    setView(nextView);
  }, []);

  const describeError = useCallback((error: unknown): string => {
    if (error instanceof GovernanceApiError) {
      setCorrelationId(error.correlationId);
      if (error.kind === "conflict") {
        return "Talep mevcut nesne durumuyla çakışıyor. Listeyi yenileyip tekrar deneyin.";
      }
      if (error.kind === "validation") {
        return "Talep doğrulanamadı. Gerekçe kodunu ve nesne durumunu kontrol edin.";
      }
      return error.message;
    }
    return "İşlem tamamlanamadı. Yeniden deneyin.";
  }, []);

  const handleDecide = useCallback(
    async (approvalRequestId: string, decision: "APPROVE" | "REJECT", reasonCode: string) => {
      setActionError(null);
      try {
        await decideGovernanceApproval(approvalRequestId, { decision, reason_code: reasonCode });
      } catch (error) {
        setActionError(describeError(error));
      }
      void load(view);
    },
    [describeError, load, view],
  );

  const handleWithdraw = useCallback(
    async (approvalRequestId: string, reasonCode: string) => {
      setActionError(null);
      try {
        await withdrawGovernanceApproval(approvalRequestId, { reason_code: reasonCode });
      } catch (error) {
        setActionError(describeError(error));
      }
      void load(view);
    },
    [describeError, load, view],
  );

  const handleApply = useCallback(
    async (approvalRequestId: string) => {
      setActionError(null);
      try {
        await applyGovernanceApproval(approvalRequestId);
      } catch (error) {
        setActionError(describeError(error));
      }
      void load(view);
    },
    [describeError, load, view],
  );

  const handleCreateRequest = useCallback(
    async (payload: {
      requestType: string;
      objectId: string;
      reasonCode: string;
      newOwnerUserId?: string;
      proposedChanges?: Record<string, unknown>;
    }) => {
      setActionError(null);
      try {
        await createGovernanceApproval({
          request_type: payload.requestType,
          object_id: payload.objectId,
          reason_code: payload.reasonCode,
          new_owner_user_id: payload.newOwnerUserId,
          proposed_changes: payload.proposedChanges,
        });
        setView("MINE");
        await load("MINE");
      } catch (error) {
        setActionError(describeError(error));
        void load(view);
      }
    },
    [describeError, load, view],
  );

  const handleLoadFields = useCallback(async (datasetId: string) => {
    const response = await listCatalogFields(datasetId);
    return response.items.map((field) => ({ id: field.data_field_id, name: field.name }));
  }, []);

  return (
    <GovernanceTasksPage
      actionError={actionError}
      correlationId={correlationId}
      datasets={datasets}
      executionOptions={executionOptions}
      items={items}
      loadFields={handleLoadFields}
      onApply={handleApply}
      onCreateRequest={canCreateRequest ? handleCreateRequest : undefined}
      onDecide={handleDecide}
      onRefresh={() => void load(view)}
      onViewChange={handleViewChange}
      onWithdraw={handleWithdraw}
      ownerCandidates={availableUsers.map((user) => ({
        id: user.user_id,
        displayName: user.display_name,
        roles: user.roles,
      }))}
      ruleOptions={ruleOptions}
      state={fixtureState ?? state}
      view={view}
    />
  );
}
