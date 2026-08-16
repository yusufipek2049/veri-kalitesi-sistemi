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
  const startInvestigation = useCallback(async (item: IssueListItem) => {
    const response = await startIssueInvestigation(item.id, item.version);
    const updated = issueFromApiItem(response.item);
    setItems((current) => current.map((candidate) => (
      candidate.id === updated.id ? updated : candidate
    )));
    setCorrelationId(response.correlation_id);
  }, []);
  const loadAssignmentOptions = useCallback(
    async (item: IssueListItem): Promise<IssueAssigneeOption[]> => {
      const response = await fetchIssueAssignmentOptions(item.id);
      setCorrelationId(response.correlation_id);
      return assigneeOptionsFromApi(response);
    },
    [],
  );
  const reassign = useCallback(async (
    item: IssueListItem,
    assigneeUserId: string,
    priority: IssuePriority,
  ) => {
    const response = await reassignIssue(
      item.id,
      item.version,
      assigneeUserId,
      priority,
    );
    const updated = issueFromApiItem(response.item);
    setItems((current) => current.map((candidate) => (
      candidate.id === updated.id ? updated : candidate
    )));
    setCorrelationId(response.correlation_id);
  }, []);
  const verify = useCallback(async (
    item: IssueListItem,
    verificationReferenceId: string,
  ) => {
    const response = await verifyIssue(
      item.id,
      item.version,
      verificationReferenceId,
    );
    const updated = issueFromApiItem(response.item);
    setItems((current) => current.map((candidate) => (
      candidate.id === updated.id ? updated : candidate
    )));
    setCorrelationId(response.correlation_id);
  }, []);
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
    const updated = issueFromApiItem(response.item);
    setItems((current) => current.map((candidate) => (
      candidate.id === updated.id ? updated : candidate
    )));
    setCorrelationId(response.correlation_id);
  }, []);
  const close = useCallback(async (item: IssueListItem) => {
    const response = await closeIssue(item.id, item.version);
    const updated = issueFromApiItem(response.item);
    setItems((current) => current.map((candidate) => (
      candidate.id === updated.id ? updated : candidate
    )));
    setCorrelationId(response.correlation_id);
  }, []);
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
  }, []);
  return (
    <IssuesPage
      correlationId={correlationId}
      items={items}
      onLoadAssignmentOptions={loadAssignmentOptions}
      onCreateIssue={fixtureState ? undefined : handleCreateIssue}
      pageActions={pageActions}
      onRefresh={() => void load()}
      onReassign={reassign}
      onLoadEvidence={loadEvidence}
      onCaptureEvidence={captureEvidence}
      onUploadEvidence={uploadEvidence}
      onDownloadEvidence={downloadEvidence}
      onResolve={resolve}
      onClose={close}
      onStartInvestigation={startInvestigation}
      onVerify={verify}
      state={fixtureState ?? state}
    />
  );
}
