import { useCallback, useEffect, useState } from "react";
import {
  captureIssueEvidence,
  downloadIssueEvidence,
  fetchIssueAssignmentOptions,
  fetchIssueEvidence,
  fetchIssues,
  uploadIssueEvidence,
  IssueApiError,
  reassignIssue,
  resolveIssue,
  startIssueInvestigation,
  verifyIssue,
  closeIssue,
  createIssue,
} from "./api";
import {
  assigneeOptionsFromApi,
  issueEvidenceCandidateFromApi,
  issueEvidenceRecordFromApi,
  issueFromApiItem,
  issuesFromApi,
  type IssueAssigneeOption,
  type IssueCreateInput,
  type IssueEvidenceCandidate,
  type IssueEvidenceRecord,
  type IssueListItem,
  type IssuePriority,
  type IssueState,
} from "./model";
import { IssuesPage } from "./IssuesPage";

const issueStates: IssueState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

// Kural: karsiliktaki guncelleyen sorun listesinin ayni kaydi degistirilir ve
// yanittaki izleme kodu sayfa seviyesinde saklanir.
function useIssueMutations({
  setItems,
  setCorrelationId,
}: {
  setItems: (updater: (current: IssueListItem[]) => IssueListItem[]) => void;
  setCorrelationId: (id: string) => void;
}) {
  const applyUpdatedItem = useCallback((item: IssueListItem) => {
    setItems((current) => current.map((candidate) => (
      candidate.id === item.id ? item : candidate
    )));
  }, [setItems]);
  const startInvestigation = useCallback(async (item: IssueListItem) => {
    const response = await startIssueInvestigation(item.id, item.version);
    applyUpdatedItem(issueFromApiItem(response.item));
    setCorrelationId(response.correlation_id);
  }, [applyUpdatedItem, setCorrelationId]);
  const reassign = useCallback(async (
    item: IssueListItem,
    assigneeUserId: string,
    priority: IssuePriority,
  ) => {
    const response = await reassignIssue(item.id, item.version, assigneeUserId, priority);
    applyUpdatedItem(issueFromApiItem(response.item));
    setCorrelationId(response.correlation_id);
  }, [applyUpdatedItem, setCorrelationId]);
  const verify = useCallback(async (
    item: IssueListItem,
    verificationReferenceId: string,
  ) => {
    const response = await verifyIssue(item.id, item.version, verificationReferenceId);
    applyUpdatedItem(issueFromApiItem(response.item));
    setCorrelationId(response.correlation_id);
  }, [applyUpdatedItem, setCorrelationId]);
  const resolve = useCallback(async (
    item: IssueListItem,
    rootCause: string,
    correctiveAction: string,
    evidenceReferenceId: string,
    completedAt: string,
  ) => {
    const response = await resolveIssue(
      item.id,
      item.version,
      rootCause,
      correctiveAction,
      evidenceReferenceId,
      completedAt,
    );
    applyUpdatedItem(issueFromApiItem(response.item));
    setCorrelationId(response.correlation_id);
  }, [applyUpdatedItem, setCorrelationId]);
  const close = useCallback(async (item: IssueListItem) => {
    const response = await closeIssue(item.id, item.version);
    applyUpdatedItem(issueFromApiItem(response.item));
    setCorrelationId(response.correlation_id);
  }, [applyUpdatedItem, setCorrelationId]);
  const handleCreateIssue = useCallback(async (input: IssueCreateInput) => {
    const idempotencyKey = crypto.randomUUID();
    const response = await createIssue({
      title: input.title,
      scope_type: input.scopeType,
      scope_id: input.scopeId,
      priority: input.priority,
      idempotency_key: idempotencyKey,
    });
    const created = issueFromApiItem(response.item);
    setItems((current) => [created, ...current]);
    setCorrelationId(response.correlation_id);
  }, [setItems, setCorrelationId]);
  return { close, handleCreateIssue, reassign, resolve, startInvestigation, verify };
}

export function IssuesRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as IssueState | null;
  const fixtureState = import.meta.env.DEV && requestedState && issueStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<IssueState>(fixtureState ?? "loading");
  const [items, setItems] = useState<IssueListItem[]>([]);
  const [correlationId, setCorrelationId] = useState<string>();
  const [pageActions, setPageActions] = useState<string[]>([]);
  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const response = await fetchIssues(signal);
      const nextItems = issuesFromApi(response);
      setItems(nextItems);
      setCorrelationId(response.correlation_id);
      setPageActions(response.available_actions ?? []);
      setState(nextItems.length ? "normal" : "empty");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof IssueApiError) {
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
  const mutations = useIssueMutations({ setItems, setCorrelationId });
  const loadAssignmentOptions = useCallback(
    async (item: IssueListItem): Promise<IssueAssigneeOption[]> => {
      const response = await fetchIssueAssignmentOptions(item.id);
      setCorrelationId(response.correlation_id);
      return assigneeOptionsFromApi(response);
    },
    [],
  );
  const loadEvidence = useCallback(
    async (item: IssueListItem): Promise<{
      records: IssueEvidenceRecord[];
      candidates: IssueEvidenceCandidate[];
    }> => {
      const response = await fetchIssueEvidence(item.id);
      setCorrelationId(response.correlation_id);
      return {
        records: response.items.map(issueEvidenceRecordFromApi),
        candidates: response.candidates.map(issueEvidenceCandidateFromApi),
      };
    },
    [],
  );
  const captureEvidence = useCallback(
    async (item: IssueListItem, candidateKey: string): Promise<IssueEvidenceRecord> => {
      const response = await captureIssueEvidence(item.id, candidateKey);
      setCorrelationId(response.correlation_id);
      return issueEvidenceRecordFromApi(response.item);
    },
    [],
  );
  const uploadEvidence = useCallback(async (item: IssueListItem, file: File, label: string,
    classification: string, onProgress: (percentage: number) => void,
  ): Promise<IssueEvidenceRecord> => {
    const response = await uploadIssueEvidence(item.id, file, label, classification, onProgress);
    setCorrelationId(response.correlation_id);
    return issueEvidenceRecordFromApi(response.item);
  }, []);
  const downloadEvidence = useCallback(async (item: IssueListItem, evidenceId: string) => {
    await downloadIssueEvidence(item.id, evidenceId);
  }, []);
  return (
    <IssuesPage
      correlationId={correlationId}
      items={items}
      onLoadAssignmentOptions={loadAssignmentOptions}
      onCreateIssue={fixtureState ? undefined : mutations.handleCreateIssue}
      pageActions={pageActions}
      onRefresh={() => void load()}
      onReassign={mutations.reassign}
      onLoadEvidence={loadEvidence}
      onCaptureEvidence={captureEvidence}
      onUploadEvidence={uploadEvidence}
      onDownloadEvidence={downloadEvidence}
      onResolve={mutations.resolve}
      onClose={mutations.close}
      onStartInvestigation={mutations.startInvestigation}
      onVerify={mutations.verify}
      state={fixtureState ?? state}
    />
  );
}
