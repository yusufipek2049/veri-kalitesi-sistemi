import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { Alert, Box, Button, Typography } from "@mui/material";
import { AppShell } from "./components/AppShell";
import { DataSourceApiError, fetchDataSources } from "./dataSources/api";
import { dataSourcesFromApi, syntheticDataSources, type DataSourceListItem, type DataSourceState } from "./dataSources/model";
import { DashboardApiError, fetchDashboardSummary } from "./dashboard/api";
import { RuleApiError, fetchRules } from "./rules/api";
import { rulesFromApi, syntheticRules, type RuleListItem, type RuleState } from "./rules/model";
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
  return <RulesPage correlationId={correlationId} items={items} onRefresh={() => void load()} state={fixtureState ?? state} />;
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
    <Suspense fallback={<Box aria-busy="true" aria-label="Sayfa yükleniyor" sx={{ minHeight: "100vh" }} />}>
      <Routes>
        <Route element={<DashboardRoute />} path="/" />
        <Route element={<DataSourcesRoute />} path="/data-sources" />
        <Route element={<RulesRoute />} path="/rules" />
        <Route element={<RouteBoundary unauthorized />} path="/unauthorized" />
        <Route element={<Navigate replace to="/not-found" />} path="/executions" />
        <Route element={<Navigate replace to="/not-found" />} path="/issues" />
        <Route element={<Navigate replace to="/not-found" />} path="/reports" />
        <Route element={<Navigate replace to="/not-found" />} path="/audit" />
        <Route element={<RouteBoundary />} path="*" />
      </Routes>
    </Suspense>
  );
}
