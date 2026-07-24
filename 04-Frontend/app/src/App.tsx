import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { Alert, Box, Button, Typography } from "@mui/material";
import { DevelopmentLoginPage, DevelopmentUserSwitcher } from "./development/DevelopmentLoginPage";
import { DevelopmentUserProvider, useDevelopmentUser } from "./development/UserContext";
import { AuditApiError, fetchAuditEvents } from "./audit/api";
import {
  auditPageFromApi,
  defaultAuditFilters,
  syntheticAuditPage,
  type AuditEventPage,
  type AuditQueryFilters,
  type AuditState,
} from "./audit/model";
import { AppShell } from "./components/AppShell";
import { DataSourceApiError, fetchDataSources } from "./dataSources/api";
import { dataSourcesFromApi, syntheticDataSources, type DataSourceListItem, type DataSourceState } from "./dataSources/model";
import { DashboardApiError, fetchDashboardSummary } from "./dashboard/api";
import { ExecutionApiError, fetchExecutions } from "./executions/api";
import { executionsFromApi, syntheticExecutions, type ExecutionListItem, type ExecutionState } from "./executions/model";
import {
  fetchIssueAssignmentOptions,
  fetchIssues,
  IssueApiError,
  reassignIssue,
  resolveIssue,
  startIssueInvestigation,
  verifyIssue,
  closeIssue,
} from "./issues/api";
import {
  assigneeOptionsFromApi,
  issueFromApiItem,
  issuesFromApi,
  syntheticIssues,
  type IssueAssigneeOption,
  type IssueListItem,
  type IssuePriority,
  type IssueState,
} from "./issues/model";
import {
  RuleApiError,
  createRule,
  createRuleVersion,
  decideRuleApproval,
  fetchRules,
  passivateRule,
  requestRuleApproval,
  testRule,
  withdrawRuleApproval,
  activateRule,
} from "./rules/api";
import { rulesFromApi, syntheticRules, type RuleCreateRequest, type RuleListItem, type RuleState, type RuleTestResult, type RuleVersionCreateRequest } from "./rules/model";
import { fetchReportSummary, ReportApiError } from "./reports/api";
import { reportSummaryFromApi, syntheticReportSummary, type ReportState, type ReportSummary } from "./reports/model";
import {
  dashboardViewModelFromApi,
  syntheticDashboardViewModel,
  type DashboardState,
  type DashboardViewModel,
} from "./dashboard/model";

const dashboardStates: DashboardState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];
const DashboardPage = lazy(() => import("./dashboard/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const DataSourcesPage = lazy(() => import("./dataSources/DataSourcesPage").then((module) => ({ default: module.DataSourcesPage })));
const RulesPage = lazy(() => import("./rules/RulesPage").then((module) => ({ default: module.RulesPage })));
const ExecutionsPage = lazy(() => import("./executions/ExecutionsPage").then((module) => ({ default: module.ExecutionsPage })));
const IssuesPage = lazy(() => import("./issues/IssuesPage").then((module) => ({ default: module.IssuesPage })));
const ReportsPage = lazy(() => import("./reports/ReportsPage").then((module) => ({ default: module.ReportsPage })));
const AuditPage = lazy(() => import("./audit/AuditPage").then((module) => ({ default: module.AuditPage })));

function DashboardRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as DashboardState | null;
  const fixtureState = import.meta.env.DEV
    && requestedState
    && dashboardStates.includes(requestedState)
    ? requestedState
    : null;
  const [state, setState] = useState<DashboardState>(fixtureState ?? "loading");
  const [data, setData] = useState<DashboardViewModel>(syntheticDashboardViewModel);
  const [correlationId, setCorrelationId] = useState<string>();

  const loadDashboard = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const response = await fetchDashboardSummary(signal);
      setData(dashboardViewModelFromApi(response));
      setCorrelationId(response.correlation_id);
      setState(response.has_data ? "normal" : "empty");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof DashboardApiError) {
        setCorrelationId(error.correlationId);
        setState(error.kind === "unauthorized" ? "unauthorized" : "error");
      } else {
        setState("error");
      }
    }
  }, [fixtureState]);

  useEffect(() => {
    const controller = new AbortController();
    void loadDashboard(controller.signal);
    return () => controller.abort();
  }, [loadDashboard]);

  return (
    <DashboardPage
      correlationId={correlationId}
      data={data}
      onRefresh={() => void loadDashboard()}
      state={fixtureState ?? state}
    />
  );
}

const dataSourceStates: DataSourceState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

function DataSourcesRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as DataSourceState | null;
  const fixtureState = import.meta.env.DEV && requestedState && dataSourceStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<DataSourceState>(fixtureState ?? "loading");
  const [items, setItems] = useState<DataSourceListItem[]>(syntheticDataSources);
  const [correlationId, setCorrelationId] = useState<string>();
  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const response = await fetchDataSources(signal);
      const nextItems = dataSourcesFromApi(response);
      setItems(nextItems);
      setCorrelationId(response.correlation_id);
      setState(nextItems.length ? "normal" : "empty");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof DataSourceApiError) {
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
  return <DataSourcesPage correlationId={correlationId} items={items} onRefresh={() => void load()} state={fixtureState ?? state} />;
}

const ruleStates: RuleState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

function RulesRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as RuleState | null;
  const fixtureState = import.meta.env.DEV && requestedState && ruleStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<RuleState>(fixtureState ?? "loading");
  const [items, setItems] = useState<RuleListItem[]>(syntheticRules);
  const [correlationId, setCorrelationId] = useState<string>();
  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const response = await fetchRules(signal);
      const nextItems = rulesFromApi(response);
      setItems(nextItems);
      setCorrelationId(response.correlation_id);
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
    const updated = rulesFromApi(response);
    setItems((current) => [...current, ...updated]);
    setCorrelationId(response.correlation_id);
  }, []);

  const handleCreateVersion = useCallback(
    async (item: RuleListItem, data: RuleVersionCreateRequest) => {
      const response = await createRuleVersion(item.id, data);
      const updated = rulesFromApi(response);
      setItems((current) => current.map((candidate) =>
        candidate.id === updated[0].id ? updated[0] : candidate,
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
    const updated = rulesFromApi(response);
    setItems((current) => current.map((candidate) =>
      candidate.id === updated[0].id ? updated[0] : candidate,
    ));
    setCorrelationId(response.correlation_id);
  }, []);

  const handleRequestApproval = useCallback(async (item: RuleListItem) => {
    const response = await requestRuleApproval(item.id);
    const updated = rulesFromApi(response);
    setItems((current) => current.map((candidate) =>
      candidate.id === updated[0].id ? updated[0] : candidate,
    ));
    setCorrelationId(response.correlation_id);
  }, []);

  const handleDecideApproval = useCallback(
    async (item: RuleListItem, approvalRequestId: string, decision: "APPROVE" | "REJECT", reasonCode: string) => {
      const response = await decideRuleApproval(approvalRequestId, { approval_request_id: approvalRequestId, decision, reason_code: reasonCode });
      const updated = rulesFromApi(response);
      setItems((current) => current.map((candidate) =>
        candidate.id === updated[0].id ? updated[0] : candidate,
      ));
      setCorrelationId(response.correlation_id);
    },
    [],
  );

  const handleWithdrawApproval = useCallback(
    async (item: RuleListItem, approvalRequestId: string, reasonCode: string) => {
      const response = await withdrawRuleApproval(approvalRequestId, { approval_request_id: approvalRequestId, reason_code: reasonCode });
      const updated = rulesFromApi(response);
      setItems((current) => current.map((candidate) =>
        candidate.id === updated[0].id ? updated[0] : candidate,
      ));
      setCorrelationId(response.correlation_id);
    },
    [],
  );

  const handlePassivateRule = useCallback(async (item: RuleListItem) => {
    const response = await passivateRule(item.id);
    const updated = rulesFromApi(response);
    setItems((current) => current.map((candidate) =>
      candidate.id === updated[0].id ? updated[0] : candidate,
    ));
    setCorrelationId(response.correlation_id);
  }, []);

  return (
    <RulesPage
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
    />
  );
}

const executionStates: ExecutionState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

function ExecutionsRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as ExecutionState | null;
  const fixtureState = import.meta.env.DEV && requestedState && executionStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<ExecutionState>(fixtureState ?? "loading");
  const [items, setItems] = useState<ExecutionListItem[]>(syntheticExecutions);
  const [correlationId, setCorrelationId] = useState<string>();
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
  return <ExecutionsPage correlationId={correlationId} items={items} onRefresh={() => void load()} state={fixtureState ?? state} />;
}

const issueStates: IssueState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

function IssuesRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as IssueState | null;
  const fixtureState = import.meta.env.DEV && requestedState && issueStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<IssueState>(fixtureState ?? "loading");
  const [items, setItems] = useState<IssueListItem[]>(syntheticIssues);
  const [correlationId, setCorrelationId] = useState<string>();
  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const response = await fetchIssues(signal);
      const nextItems = issuesFromApi(response);
      setItems(nextItems);
      setCorrelationId(response.correlation_id);
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
  return (
    <IssuesPage
      correlationId={correlationId}
      items={items}
      onLoadAssignmentOptions={loadAssignmentOptions}
      onRefresh={() => void load()}
      onReassign={reassign}
      onResolve={resolve}
      onClose={close}
      onStartInvestigation={startInvestigation}
      onVerify={verify}
      state={fixtureState ?? state}
    />
  );
}

const reportStates: ReportState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

function ReportsRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as ReportState | null;
  const fixtureState = import.meta.env.DEV && requestedState && reportStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<ReportState>(fixtureState ?? "loading");
  const [summary, setSummary] = useState<ReportSummary>(syntheticReportSummary);
  const [correlationId, setCorrelationId] = useState<string>();
  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const response = await fetchReportSummary(signal);
      const nextSummary = reportSummaryFromApi(response);
      setSummary(nextSummary);
      setCorrelationId(response.correlation_id);
      setState(nextSummary.rows.length ? "normal" : "empty");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof ReportApiError) {
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
  return <ReportsPage correlationId={correlationId} onRefresh={() => void load()} state={fixtureState ?? state} summary={summary} />;
}

const auditStates: AuditState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

function AuditRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as AuditState | null;
  const fixtureState = import.meta.env.DEV && requestedState && auditStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<AuditState>(fixtureState ?? "loading");
  const [page, setPage] = useState<AuditEventPage>(syntheticAuditPage);
  const [filters, setFilters] = useState<AuditQueryFilters>(defaultAuditFilters);
  const [correlationId, setCorrelationId] = useState<string>();
  const load = useCallback(async (
    nextFilters: AuditQueryFilters,
    append = false,
    signal?: AbortSignal,
  ) => {
    if (fixtureState) return;
    if (!append) setState("loading");
    try {
      const response = await fetchAuditEvents(nextFilters, {
        afterSequenceNo: append ? page.nextAfterSequenceNo ?? undefined : undefined,
        periodEnd: append ? page.periodEnd : undefined,
        throughSequenceNo: append ? page.throughSequenceNo : undefined,
        signal,
      });
      const nextPage = auditPageFromApi(response);
      setPage((current) => append
        ? { ...nextPage, items: [...current.items, ...nextPage.items] }
        : nextPage);
      setCorrelationId(response.correlation_id);
      setState((append ? page.items.length + nextPage.items.length : nextPage.items.length) ? "normal" : "empty");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof AuditApiError) {
        setCorrelationId(error.correlationId);
        setState(error.kind === "unauthorized" ? "unauthorized" : "error");
      } else setState("error");
    }
  }, [fixtureState, page.items.length, page.nextAfterSequenceNo, page.throughSequenceNo]);
  useEffect(() => {
    const controller = new AbortController();
    void load(defaultAuditFilters, false, controller.signal);
    return () => controller.abort();
  }, [fixtureState]);
  const query = (nextFilters: AuditQueryFilters) => {
    setFilters(nextFilters);
    void load(nextFilters);
  };
  return <AuditPage correlationId={correlationId} onLoadMore={() => void load(filters, true)} onQuery={query} onRefresh={() => void load(filters)} page={page} state={fixtureState ?? state} />;
}

function RouteBoundary({ unauthorized = false }: { unauthorized?: boolean }) {
  const navigate = useNavigate();
  return (
    <AppShell currentPage={unauthorized ? "Erişim" : "Sayfa Bulunamadı"}>
      <Box sx={(theme) => ({ margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 6 } })}>
        <Alert severity={unauthorized ? "warning" : "info"}>
          <Typography sx={{ fontWeight: 700 }}>{unauthorized ? "Bu görünüm için yetkiniz yok" : "Sayfa bulunamadı"}</Typography>
          <Typography variant="body2">{unauthorized ? "İstenen içeriğe erişim verilmedi." : "İstenen rota mevcut değil veya henüz kullanıma açılmadı."}</Typography>
          <Button color="inherit" onClick={() => navigate("/")} sx={{ mt: 2 }}>Genel bakışa dön</Button>
        </Alert>
      </Box>
    </AppShell>
  );
}

export default function App() {
  return (
    <DevelopmentUserProvider>
      <AppContent />
      <DevelopmentUserSwitcher />
    </DevelopmentUserProvider>
  );
}

function AppContent() {
  const { currentUser, isLoading } = useDevelopmentUser();

  const showLogin = !isLoading && !currentUser;

  if (isLoading) {
    return (
      <Box aria-busy="true" aria-label="Yükleniyor" sx={{ minHeight: "100vh" }} />
    );
  }

  if (showLogin) {
    return <DevelopmentLoginPage />;
  }

  return (
    <Suspense fallback={<Box aria-busy="true" aria-label="Sayfa yükleniyor" sx={{ minHeight: "100vh" }} />}>
      <Routes>
        <Route element={<DashboardRoute />} path="/" />
        <Route element={<DataSourcesRoute />} path="/data-sources" />
        <Route element={<RulesRoute />} path="/rules" />
        <Route element={<ExecutionsRoute />} path="/executions" />
        <Route element={<IssuesRoute />} path="/issues" />
        <Route element={<RouteBoundary unauthorized />} path="/unauthorized" />
        <Route element={<ReportsRoute />} path="/reports" />
        <Route element={<AuditRoute />} path="/audit" />
        <Route element={<RouteBoundary />} path="*" />
      </Routes>
    </Suspense>
  );
}
