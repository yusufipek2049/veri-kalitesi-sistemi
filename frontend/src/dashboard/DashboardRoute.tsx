import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { DashboardApiError, fetchDashboardSummary } from "./api";
import {
  dashboardViewModelFromApi,
  filtersFromSearchParams,
  hasInvalidFilterParams,
  isFiltersEmpty,
  syntheticDashboardViewModel,
  type AppliedDashboardFilters,
  type DashboardFilters,
  type DashboardState,
  type DashboardViewModel,
} from "./model";
import { DashboardPage } from "./DashboardPage";

const dashboardStates: DashboardState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

export function DashboardRoute() {
  const navigate = useNavigate();
  const searchParams = new URLSearchParams(window.location.search);
  const requestedState = searchParams.get("state") as DashboardState | null;
  const fixtureState = import.meta.env.DEV
    && requestedState
    && dashboardStates.includes(requestedState)
    ? requestedState
    : null;

  const invalidParams = hasInvalidFilterParams(searchParams);
  const initialFilters = invalidParams ? {} : filtersFromSearchParams(searchParams);

  const [state, setState] = useState<DashboardState>(
    fixtureState ?? (invalidParams ? "invalid-filter" : "loading"),
  );
  const [data, setData] = useState<DashboardViewModel>(syntheticDashboardViewModel);
  const [correlationId, setCorrelationId] = useState<string>();
  const [filters, setFilters] = useState<DashboardFilters>(initialFilters);
  const [appliedFilters, setAppliedFilters] = useState<AppliedDashboardFilters | null>(null);

  const loadDashboard = useCallback(async (currentFilters: DashboardFilters, signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const response = await fetchDashboardSummary(
        isFiltersEmpty(currentFilters) ? undefined : currentFilters,
        signal,
      );
      setData(dashboardViewModelFromApi(response));
      setCorrelationId(response.correlation_id);
      setAppliedFilters(response.applied_filters ?? null);
      setState(response.has_data ? "normal" : "empty");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof DashboardApiError) {
        setCorrelationId(error.correlationId);
        if (error.kind === "unauthorized") setState("unauthorized");
        else if (error.kind === "scope-forbidden") setState("scope-forbidden");
        else if (error.kind === "invalid-filter") setState("invalid-filter");
        else setState("error");
      } else {
        setState("error");
      }
    }
  }, [fixtureState]);

  useEffect(() => {
    const controller = new AbortController();
    void loadDashboard(filters, controller.signal);
    return () => controller.abort();
  }, [loadDashboard, filters]);

  const handleFiltersChange = useCallback((nextFilters: DashboardFilters) => {
    setFilters(nextFilters);
    const params = new URLSearchParams();
    if (nextFilters.scope_type) params.set("scope_type", nextFilters.scope_type);
    if (nextFilters.scope_id) params.set("scope_id", nextFilters.scope_id);
    if (nextFilters.score_status) params.set("score_status", nextFilters.score_status);
    if (nextFilters.level) params.set("level", nextFilters.level);
    navigate({ search: params.toString() ? `?${params.toString()}` : "" }, { replace: true });
  }, [navigate]);

  const handleClearFilters = useCallback(() => {
    handleFiltersChange({});
  }, [handleFiltersChange]);

  return (
    <DashboardPage
      appliedFilters={appliedFilters}
      correlationId={correlationId}
      data={data}
      filters={filters}
      onClearFilters={handleClearFilters}
      onFiltersChange={handleFiltersChange}
      onRefresh={() => void loadDashboard(filters)}
      state={fixtureState ?? state}
    />
  );
}
