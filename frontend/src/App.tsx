import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { Alert, Box, Button, Typography } from "@mui/material";
import { DevelopmentLoginPage, DevelopmentUserSwitcher } from "./development/DevelopmentLoginPage";
import { DevelopmentUserProvider, useDevelopmentUser } from "./development/UserContext";
import { AuditRoute } from "./audit/AuditRoute";
import { AppShell } from "./components/AppShell";
import {
  CatalogApiError,
  applyMetadataDiff,
  getCatalogDataset,
  getCatalogField,
  getDiscoveryStatus,
  listCatalogDatasets,
  listCatalogFields,
  requestMetadataDiscovery,
} from "./catalog/api";
import {
  mapCatalogDataset,
  mapCatalogField,
  mapDiscoveryStatus,
  type CatalogDataset,
  type CatalogField,
  type CatalogPageState,
  type DatasetDetailState,
  type DiscoveryStatus,
  type FieldDetailState,
  type MetadataDiff,
} from "./catalog/model";
import { DataSourcesRoute } from "./dataSources/DataSourcesRoute";
import { ExecutionsRoute } from "./executions/ExecutionsRoute";
import { IssuesRoute } from "./issues/IssuesRoute";
import { fetchChannels, fetchInbox, fetchSubscriptions, fetchUnreadCount, markDeliveryRead } from "./notifications/api";
import { RulesRoute } from "./rules/RulesRoute";

const CatalogPage = lazy(() => import("./catalog/CatalogPage").then((module) => ({ default: module.CatalogPage })));
const DatasetDetailPage = lazy(() => import("./catalog/DatasetDetailPage").then((module) => ({ default: module.DatasetDetailPage })));
const FieldDetailPage = lazy(() => import("./catalog/FieldDetailPage").then((module) => ({ default: module.FieldDetailPage })));
const ScoresPage = lazy(() => import("./scores/ScoresPage").then((module) => ({ default: module.ScoresPage })));
const ScoreDetailPage = lazy(() => import("./scores/ScoreDetailPage").then((module) => ({ default: module.ScoreDetailPage })));
const ScoreComparisonPage = lazy(() => import("./scores/ScoreComparisonPage").then((module) => ({ default: module.ScoreComparisonPage })));
const NotificationsPage = lazy(() => import("./notifications/NotificationsPage").then((module) => ({ default: module.NotificationsPage })));
const NotificationPreferencesPage = lazy(() => import("./notifications/NotificationPreferencesPage").then((module) => ({ default: module.NotificationPreferencesPage })));
const NotificationChannelsPage = lazy(() => import("./notifications/NotificationChannelsPage").then((module) => ({ default: module.NotificationChannelsPage })));
const NotificationDeliveriesPage = lazy(() => import("./notifications/NotificationDeliveriesPage").then((module) => ({ default: module.NotificationDeliveriesPage })));

function NotificationsRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as "normal" | "loading" | "empty" | "error" | "unauthorized" | null;
  const fixtureState = import.meta.env.DEV && requestedState && ["normal", "loading", "empty", "error", "unauthorized"].includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<"normal" | "loading" | "empty" | "error" | "unauthorized">(fixtureState ?? "loading");
  const [items, setItems] = useState<import("./notifications/model").NotificationDelivery[]>([]);
  const [totalUnread, setTotalUnread] = useState(0);
  const [correlationId, setCorrelationId] = useState<string>();
  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const [inbox, count] = await Promise.all([
        fetchInbox({ limit: 50 }),
        fetchUnreadCount(),
      ]);
      if (signal?.aborted) return;
      setItems(inbox.deliveries);
      setTotalUnread(count);
      setState(inbox.deliveries.length ? "normal" : "empty");
    } catch {
      if (signal?.aborted) return;
      setState("error");
    }
  }, [fixtureState]);
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [fixtureState]);
  const handleMarkRead = useCallback(async (deliveryId: string) => {
    try {
      await markDeliveryRead(deliveryId);
      setItems((current) => current.map((item) => item.deliveryId === deliveryId ? { ...item, status: "READ" as const, readAt: new Date().toISOString() } : item));
      setTotalUnread((current) => Math.max(0, current - 1));
    } catch {
      // Read failure is non-fatal; the item stays in its current state.
    }
  }, []);
  return (
    <NotificationsPage
      correlationId={correlationId}
      items={items}
      onMarkRead={(id) => void handleMarkRead(id)}
      onRefresh={() => void load()}
      state={fixtureState ?? state}
      totalUnread={totalUnread}
    />
  );
}

function NotificationPreferencesRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as "normal" | "loading" | "empty" | "error" | "unauthorized" | null;
  const fixtureState = import.meta.env.DEV && requestedState && ["normal", "loading", "empty", "error", "unauthorized"].includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<"normal" | "loading" | "empty" | "error" | "unauthorized">(fixtureState ?? "loading");
  const [subscriptions, setSubscriptions] = useState<import("./notifications/model").NotificationSubscription[]>([]);
  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const result = await fetchSubscriptions();
      if (signal?.aborted) return;
      setSubscriptions(result);
      setState(result.length ? "normal" : "empty");
    } catch {
      if (signal?.aborted) return;
      setState("error");
    }
  }, [fixtureState]);
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [fixtureState]);
  return (
    <NotificationPreferencesPage
      onRefresh={() => void load()}
      state={fixtureState ?? state}
      subscriptions={subscriptions}
    />
  );
}

function NotificationChannelsRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as "normal" | "loading" | "empty" | "error" | "unauthorized" | null;
  const fixtureState = import.meta.env.DEV && requestedState && ["normal", "loading", "empty", "error", "unauthorized"].includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<"normal" | "loading" | "empty" | "error" | "unauthorized">(fixtureState ?? "loading");
  const [channels, setChannels] = useState<import("./notifications/model").NotificationChannel[]>([]);
  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const result = await fetchChannels();
      if (signal?.aborted) return;
      setChannels(result);
      setState(result.length ? "normal" : "empty");
    } catch {
      if (signal?.aborted) return;
      setState("error");
    }
  }, [fixtureState]);
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [fixtureState]);
  return (
    <NotificationChannelsPage
      channels={channels}
      onRefresh={() => void load()}
      state={fixtureState ?? state}
    />
  );
}

function NotificationDeliveriesRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as "normal" | "loading" | "empty" | "error" | "unauthorized" | null;
  const fixtureState = import.meta.env.DEV && requestedState && ["normal", "loading", "empty", "error", "unauthorized"].includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<"normal" | "loading" | "empty" | "error" | "unauthorized">(fixtureState ?? "loading");
  const [items, setItems] = useState<import("./notifications/model").NotificationDelivery[]>([]);
  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const result = await fetchInbox({ limit: 100 });
      if (signal?.aborted) return;
      setItems(result.deliveries);
      setState(result.deliveries.length ? "normal" : "empty");
    } catch {
      if (signal?.aborted) return;
      setState("error");
    }
  }, [fixtureState]);
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [fixtureState]);
  return (
    <NotificationDeliveriesPage
      items={items}
      onRefresh={() => void load()}
      state={fixtureState ?? state}
    />
  );
}

const catalogPageStates: CatalogPageState[] = ["normal", "loading", "empty", "error", "unauthorized"];

function CatalogRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as CatalogPageState | null;
  const fixtureState = import.meta.env.DEV && requestedState && catalogPageStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<CatalogPageState>(fixtureState ?? "loading");
  const [items, setItems] = useState<CatalogDataset[]>([]);
  const [correlationId, setCorrelationId] = useState<string>();

  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const response = await listCatalogDatasets(undefined);
      if (signal?.aborted) return;
      const mapped = response.items.map(mapCatalogDataset);
      setItems(mapped);
      setCorrelationId(response.correlation_id);
      setState(mapped.length ? "normal" : "empty");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof CatalogApiError) {
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

  return (
    <CatalogPage
      correlationId={correlationId}
      items={items}
      onRefresh={() => void load()}
      state={fixtureState ?? state}
    />
  );
}

const datasetDetailStates: DatasetDetailState[] = ["normal", "loading", "error", "unauthorized", "not-found"];

function DatasetDetailRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as DatasetDetailState | null;
  const fixtureState = import.meta.env.DEV && requestedState && datasetDetailStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<DatasetDetailState>(fixtureState ?? "loading");
  const [dataset, setDataset] = useState<CatalogDataset | undefined>();
  const [dataSourceName, setDataSourceName] = useState<string>();
  const [fields, setFields] = useState<CatalogField[]>([]);
  const [discoveryStatus, setDiscoveryStatus] = useState<DiscoveryStatus | null>(null);
  const [latestDiff, setLatestDiff] = useState<MetadataDiff | null>(null);
  const [correlationId, setCorrelationId] = useState<string>();

  const datasetId = window.location.pathname.split("/").pop() ?? "";

  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const detailResponse = await getCatalogDataset(datasetId);
      if (signal?.aborted) return;
      const mappedDataset = mapCatalogDataset(detailResponse.dataset);
      setDataset(mappedDataset);
      setDataSourceName(detailResponse.data_source_name);
      setCorrelationId(detailResponse.correlation_id);

      const fieldsResponse = await listCatalogFields(datasetId);
      if (signal?.aborted) return;
      setFields(fieldsResponse.items.map(mapCatalogField));
      setState("normal");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof CatalogApiError) {
        setCorrelationId(error.correlationId);
        if (error.kind === "unauthorized") setState("unauthorized");
        else if (error.kind === "not-found") setState("not-found");
        else setState("error");
      } else setState("error");
    }
  }, [fixtureState, datasetId]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const handleRequestDiscovery = useCallback(async (sourceId: string) => {
    const response = await requestMetadataDiscovery(sourceId);
    setCorrelationId(response.correlation_id);
    const statusResponse = await getDiscoveryStatus(response.discovery_id);
    setDiscoveryStatus(mapDiscoveryStatus(statusResponse));
  }, []);

  const handleApplyDiff = useCallback(async (metadataDiffId: string) => {
    const response = await applyMetadataDiff(metadataDiffId, {
      reason_code: "USER_APPLIED",
      expected_version: latestDiff?.metadataDiffId ? 1 : 1,
    });
    setCorrelationId(response.correlation_id);
    setLatestDiff(null);
    void load();
  }, [latestDiff, load]);

  return (
    <DatasetDetailPage
      correlationId={correlationId}
      dataset={dataset}
      dataSourceName={dataSourceName}
      discoveryStatus={discoveryStatus}
      fields={fields}
      latestDiff={latestDiff}
      onApplyDiff={fixtureState ? undefined : handleApplyDiff}
      onRefresh={() => void load()}
      onRequestDiscovery={fixtureState ? undefined : handleRequestDiscovery}
      state={fixtureState ?? state}
    />
  );
}

const fieldDetailStates: FieldDetailState[] = ["normal", "loading", "error", "unauthorized", "not-found"];

function FieldDetailRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as FieldDetailState | null;
  const fixtureState = import.meta.env.DEV && requestedState && fieldDetailStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<FieldDetailState>(fixtureState ?? "loading");
  const [field, setField] = useState<CatalogField | undefined>();
  const [datasetName, setDatasetName] = useState<string>();
  const [dataSourceName, setDataSourceName] = useState<string>();
  const [correlationId, setCorrelationId] = useState<string>();

  const fieldId = window.location.pathname.split("/").pop() ?? "";

  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const response = await getCatalogField(fieldId);
      if (signal?.aborted) return;
      setField(mapCatalogField(response.field));
      setDatasetName(response.dataset_name);
      setDataSourceName(response.data_source_name);
      setCorrelationId(response.correlation_id);
      setState("normal");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof CatalogApiError) {
        setCorrelationId(error.correlationId);
        if (error.kind === "unauthorized") setState("unauthorized");
        else if (error.kind === "not-found") setState("not-found");
        else setState("error");
      } else setState("error");
    }
  }, [fixtureState, fieldId]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  return (
    <FieldDetailPage
      correlationId={correlationId}
      datasetName={datasetName}
      dataSourceName={dataSourceName}
      field={field}
      onRefresh={() => void load()}
      state={fixtureState ?? state}
    />
  );
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
      <ApplicationRoutes />
    </Suspense>
  );
}

export function ApplicationRoutes() {
  return (
    <Routes>
      <Route element={<Navigate replace to="/data-sources" />} path="/" />
      <Route element={<DataSourcesRoute />} path="/data-sources" />
      <Route element={<CatalogRoute />} path="/catalog" />
      <Route element={<DatasetDetailRoute />} path="/catalog/datasets/:datasetId" />
      <Route element={<FieldDetailRoute />} path="/catalog/fields/:fieldId" />
      <Route element={<RulesRoute />} path="/rules" />
      <Route element={<ExecutionsRoute />} path="/executions" />
      <Route element={<ScoresPage />} path="/scores" />
      <Route element={<ScoreDetailPage />} path="/scores/:scoreId" />
      <Route element={<ScoreComparisonPage />} path="/scores/comparison" />
      <Route element={<IssuesRoute />} path="/issues" />
      <Route element={<RouteBoundary unauthorized />} path="/unauthorized" />
      <Route element={<AuditRoute />} path="/audit" />
      <Route element={<NotificationsRoute />} path="/notifications" />
      <Route element={<NotificationPreferencesRoute />} path="/notifications/preferences" />
      <Route element={<NotificationChannelsRoute />} path="/notifications/channels" />
      <Route element={<NotificationDeliveriesRoute />} path="/notifications/deliveries" />
      <Route element={<RouteBoundary />} path="*" />
    </Routes>
  );
}
