import { useCallback, useEffect, useState } from "react";
import { DashboardApiError, fetchDashboardSummary } from "./dashboard/api";
import { DashboardPage } from "./dashboard/DashboardPage";
import {
  dashboardViewModelFromApi,
  syntheticDashboardViewModel,
  type DashboardState,
  type DashboardViewModel,
} from "./dashboard/model";

const dashboardStates: DashboardState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

export default function App() {
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
