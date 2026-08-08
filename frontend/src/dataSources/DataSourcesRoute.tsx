import { useCallback, useEffect, useState } from "react";
import { DataSourceApiError, createDataSource, decideDataSourceActivation, fetchDataSources, passivateDataSource, requestDataSourceActivation, testDataSource } from "./api";
import { dataSourceFromApi, dataSourcesFromApi, syntheticDataSources, type DataSourceCreateRequest, type DataSourceListItem, type DataSourceState } from "./model";
import { DataSourcesPage } from "./DataSourcesPage";
import { discoverMetadata } from "./api";

const dataSourceStates: DataSourceState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

export function DataSourcesRoute() {
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

  const handleCreate = useCallback(async (payload: DataSourceCreateRequest) => {
    const response = await createDataSource(payload);
    const updated = dataSourceFromApi(response.item);
    setItems((current) => [...current, updated]);
    setCorrelationId(response.correlation_id);
  }, []);

  const handleTest = useCallback(async (dataSourceId: string) => {
    const response = await testDataSource(dataSourceId);
    const updated = dataSourceFromApi(response.item);
    setItems((current) => current.map((candidate) =>
      candidate.id === updated.id ? updated : candidate,
    ));
    setCorrelationId(response.correlation_id);
  }, []);

  const handleRequestActivation = useCallback(async (dataSourceId: string) => {
    const response = await requestDataSourceActivation(dataSourceId);
    const updated = dataSourceFromApi(response.item);
    setItems((current) => current.map((candidate) =>
      candidate.id === updated.id ? updated : candidate,
    ));
    setCorrelationId(response.correlation_id);
  }, []);

  const handleDecideActivation = useCallback(async (
    activationRequestId: string,
    decision: "APPROVE" | "REJECT",
    reasonCode: string,
  ) => {
    const response = await decideDataSourceActivation(activationRequestId, decision, reasonCode);
    const updated = dataSourceFromApi(response.item);
    setItems((current) => current.map((candidate) =>
      candidate.id === updated.id ? updated : candidate,
    ));
    setCorrelationId(response.correlation_id);
  }, []);

  const handlePassivate = useCallback(async (dataSourceId: string, reasonCode: string) => {
    const response = await passivateDataSource(dataSourceId, reasonCode);
    const updated = dataSourceFromApi(response.item);
    setItems((current) => current.map((candidate) =>
      candidate.id === updated.id ? updated : candidate,
    ));
    setCorrelationId(response.correlation_id);
  }, []);

  const handleDiscoverMetadata = useCallback(async (dataSourceId: string) => {
    await discoverMetadata(dataSourceId);
  }, []);

  return (
    <DataSourcesPage
      correlationId={correlationId}
      items={items}
      onRefresh={() => void load()}
      state={fixtureState ?? state}
      onCreate={fixtureState ? undefined : handleCreate}
      onTest={fixtureState ? undefined : handleTest}
      onRequestActivation={fixtureState ? undefined : handleRequestActivation}
      onDecideActivation={fixtureState ? undefined : handleDecideActivation}
      onPassivate={fixtureState ? undefined : handlePassivate}
      onDiscoverMetadata={fixtureState ? undefined : handleDiscoverMetadata}
    />
  );
}
