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
  getDiscoveryDiff,
  listCatalogDatasets,
  listCatalogFields,
  pollDiscoveryStatus,
  requestMetadataDiscovery,
  updateDataset,
  updateField,
} from "./catalog/api";
import {
  mapCatalogDataset,
  mapCatalogField,
  mapDiscoveryStatus,
  mapMetadataDiff,
  type CatalogDataset,
  type CatalogField,
  type CatalogPageState,
  type DatasetDetailState,
  type DatasetUpdatePayload,
  type DiscoveryStatus,
  type FieldDetailState,
  type FieldUpdatePayload,
  type MetadataDiff,
} from "./catalog/model";
import { DataSourcesRoute } from "./dataSources/DataSourcesRoute";
import { ExecutionsRoute } from "./executions/ExecutionsRoute";
import { GovernanceTasksRoute } from "./governance/GovernanceTasksRoute";
import { RuleHealthPage } from "./analytics/RuleHealthPage";
import { MetadataHealthPage } from "./analytics/MetadataHealthPage";
import { IssuePerformancePage } from "./analytics/IssuePerformancePage";
import { ScoringPolicyImpactPage } from "./analytics/ScoringPolicyImpactPage";
import { IssuesRoute } from "./issues/IssuesRoute";
import { fetchChannels, fetchInbox, fetchSubscriptions, fetchUnreadCount, markAllRead, bulkMarkRead, markDeliveryRead } from "./notifications/api";
import type { NotificationChannel, NotificationDelivery, NotificationSubscription } from "./notifications/model";
import { useNotificationRoute } from "./notifications/useNotificationRoute";
import { RulesRoute } from "./rules/RulesRoute";
import { fetchRules } from "./rules/api";
import { rulesFromApi } from "./rules/model";
import { LauncherControlProvider } from "./launcherControl";

const CatalogPage = lazy(() => import("./catalog/CatalogPage").then((module) => ({ default: module.CatalogPage })));
const DatasetDetailPage = lazy(() => import("./catalog/DatasetDetailPage").then((module) => ({ default: module.DatasetDetailPage })));
const FieldDetailPage = lazy(() => import("./catalog/FieldDetailPage").then((module) => ({ default: module.FieldDetailPage })));
const DashboardPage = lazy(() => import("./dashboard/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const ScoresPage = lazy(() => import("./scores/ScoresPage").then((module) => ({ default: module.ScoresPage })));
const ScoreDetailPage = lazy(() => import("./scores/ScoreDetailPage").then((module) => ({ default: module.ScoreDetailPage })));
const ScoreComparisonPage = lazy(() => import("./scores/ScoreComparisonPage").then((module) => ({ default: module.ScoreComparisonPage })));
const DatasetTrendPage = lazy(() => import("./scores/DatasetTrendPage").then((module) => ({ default: module.DatasetTrendPage })));
const NotificationsPage = lazy(() => import("./notifications/NotificationsPage").then((module) => ({ default: module.NotificationsPage })));
const NotificationPreferencesPage = lazy(() => import("./notifications/NotificationPreferencesPage").then((module) => ({ default: module.NotificationPreferencesPage })));
const NotificationChannelsPage = lazy(() => import("./notifications/NotificationChannelsPage").then((module) => ({ default: module.NotificationChannelsPage })));
const NotificationDeliveriesPage = lazy(() => import("./notifications/NotificationDeliveriesPage").then((module) => ({ default: module.NotificationDeliveriesPage })));

interface NotificationsRouteData {
  items: NotificationDelivery[];
  totalUnread: number;
  failedCount: number;
  todayCount: number;
  cursor: string | null;
  hasMore: boolean;
}

async function loadNotifications(): Promise<{ data: NotificationsRouteData; isEmpty: boolean }> {
  const [inbox, totalUnread] = await Promise.all([
    fetchInbox({ limit: 50 }),
    fetchUnreadCount(),
  ]);
  return {
    data: {
      items: inbox.deliveries,
      totalUnread,
      failedCount: inbox.failedCount,
      todayCount: inbox.todayCount,
      cursor: inbox.cursor,
      hasMore: inbox.hasMore,
    },
    isEmpty: inbox.deliveries.length === 0,
  };
}

async function loadNotificationSubscriptions(): Promise<{ data: NotificationSubscription[]; isEmpty: boolean }> {
  const subscriptions = await fetchSubscriptions();
  return { data: subscriptions, isEmpty: subscriptions.length === 0 };
}

async function loadNotificationChannels(): Promise<{ data: NotificationChannel[]; isEmpty: boolean }> {
  const channels = await fetchChannels();
  return { data: channels, isEmpty: channels.length === 0 };
}

async function loadNotificationDeliveries(): Promise<{ data: NotificationDelivery[]; isEmpty: boolean }> {
  const inbox = await fetchInbox({ limit: 100 });
  return { data: inbox.deliveries, isEmpty: inbox.deliveries.length === 0 };
}

function NotificationsRoute() {
  const { data, load, setData, state } = useNotificationRoute<NotificationsRouteData>(
    { items: [], totalUnread: 0, failedCount: 0, todayCount: 0, cursor: null, hasMore: false },
    loadNotifications,
  );
  const handleMarkRead = useCallback(async (deliveryId: string) => {
    try {
      await markDeliveryRead(deliveryId);
      setData((current) => ({
        items: current.items.map((item) => item.deliveryId === deliveryId ? { ...item, status: "READ" as const, readAt: new Date().toISOString() } : item),
        totalUnread: Math.max(0, current.totalUnread - 1),
        failedCount: current.failedCount,
        todayCount: current.todayCount,
        cursor: current.cursor,
        hasMore: current.hasMore,
      }));
    } catch (error) {
      console.warn("Bildirim okundu işaretleme başarısız:", error);
    }
  }, [setData]);
  const handleMarkAllRead = useCallback(async () => {
    try {
      const marked = await markAllRead();
      setData((current) => ({
        ...current,
        items: current.items.map((item) => item.status === "DELIVERED" ? { ...item, status: "READ" as const, readAt: new Date().toISOString() } : item),
        totalUnread: Math.max(0, current.totalUnread - marked),
      }));
    } catch (error) {
      console.warn("Tüm bildirimleri okundu işaretleme başarısız:", error);
    }
  }, [setData]);
  const handleBulkMarkRead = useCallback(async (deliveryIds: string[]) => {
    try {
      const marked = await bulkMarkRead(deliveryIds);
      const idSet = new Set(deliveryIds);
      setData((current) => ({
        ...current,
        items: current.items.map((item) => idSet.has(item.deliveryId) && item.status === "DELIVERED" ? { ...item, status: "READ" as const, readAt: new Date().toISOString() } : item),
        totalUnread: Math.max(0, current.totalUnread - marked),
      }));
    } catch (error) {
      console.warn("Toplu bildirim okundu işaretleme başarısız:", error);
    }
  }, [setData]);
  const handleLoadMore = useCallback(async () => {
    if (!data.cursor) return;
    try {
      const more = await fetchInbox({ limit: 50, cursor: data.cursor });
      setData((current) => ({
        ...current,
        items: [...current.items, ...more.deliveries],
        cursor: more.cursor,
        hasMore: more.hasMore,
      }));
    } catch {
      // Non-fatal
    }
  }, [data.cursor, setData]);
  return (
    <NotificationsPage
      cursor={data.cursor}
      failedCount={data.failedCount}
      hasMore={data.hasMore}
      items={data.items}
      onLoadMore={() => void handleLoadMore()}
      onBulkMarkRead={(ids) => void handleBulkMarkRead(ids)}
      onMarkAllRead={() => void handleMarkAllRead()}
      onMarkRead={(id) => void handleMarkRead(id)}
      onRefresh={() => void load()}
      state={state}
      todayCount={data.todayCount}
      totalUnread={data.totalUnread}
    />
  );
}

function NotificationPreferencesRoute() {
  const { data, load, state } = useNotificationRoute<NotificationSubscription[]>([], loadNotificationSubscriptions);
  return (
    <NotificationPreferencesPage
      onRefresh={() => void load()}
      state={state}
      subscriptions={data}
    />
  );
}

function NotificationChannelsRoute() {
  const { data, load, state } = useNotificationRoute<NotificationChannel[]>([], loadNotificationChannels);
  return (
    <NotificationChannelsPage
      channels={data}
      onRefresh={() => void load()}
      state={state}
    />
  );
}

function NotificationDeliveriesRoute() {
  const { data, load, state } = useNotificationRoute<NotificationDelivery[]>([], loadNotificationDeliveries);
  return (
    <NotificationDeliveriesPage
      items={data}
      onRefresh={() => void load()}
      state={state}
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
  const [datasetRules, setDatasetRules] = useState<Array<{ id: string; code: string; name: string; dimension: string; status: string; criticality: string; ruleType: string }>>([]);
  const [discoveryStatus, setDiscoveryStatus] = useState<DiscoveryStatus | null>(null);
  const [latestDiff, setLatestDiff] = useState<MetadataDiff | null>(null);
  const [correlationId, setCorrelationId] = useState<string>();

  const datasetId = window.location.pathname.split("/").pop() ?? "";

  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const [detailResponse, rulesResponse] = await Promise.all([
        getCatalogDataset(datasetId),
        fetchRules(signal).catch(() => null),
      ]);
      if (signal?.aborted) return;
      const mappedDataset = mapCatalogDataset(detailResponse.dataset);
      setDataset(mappedDataset);
      setDataSourceName(detailResponse.data_source_name);
      setCorrelationId(detailResponse.correlation_id);

      const fieldsResponse = await listCatalogFields(datasetId);
      if (signal?.aborted) return;
      setFields(fieldsResponse.items.map(mapCatalogField));

      // Filter rules for this dataset
      if (rulesResponse) {
        const allRules = rulesFromApi(rulesResponse);
        setDatasetRules(
          allRules
            .filter((r) => r.datasetId === datasetId)
            .map((r) => ({
              id: r.id,
              code: r.code,
              name: r.name,
              dimension: r.dimension,
              status: r.status,
              criticality: r.criticality,
              ruleType: r.ruleType,
            })),
        );
      }

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
    // Poll until terminal state or timeout (60s)
    const finalStatus = await pollDiscoveryStatus(response.discovery_id, {
      intervalMs: 3000,
      timeoutMs: 60_000,
      onProgress: (status) => {
        setDiscoveryStatus(mapDiscoveryStatus(status));
      },
    });
    setDiscoveryStatus(mapDiscoveryStatus(finalStatus));
    // Fetch diff if discovery succeeded
    if (finalStatus.status === "SUCCESS" || finalStatus.status === "PARTIAL") {
      try {
        const diffResponse = await getDiscoveryDiff(response.discovery_id);
        if (diffResponse.metadata_diff_id) {
          setLatestDiff(mapMetadataDiff(diffResponse));
        }
      } catch {
        // Diff fetch failure is non-fatal
      }
    }
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

  const handleUpdateDataset = useCallback(async (payload: DatasetUpdatePayload) => {
    if (!dataset) return;
    const response = await updateDataset(dataset.id, payload);
    setDataset(mapCatalogDataset(response.dataset));
    setCorrelationId(response.correlation_id);
  }, [dataset]);

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
      onUpdateDataset={fixtureState ? undefined : handleUpdateDataset}
      rules={datasetRules}
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

  const handleUpdateField = useCallback(async (payload: FieldUpdatePayload) => {
    if (!field) return;
    const response = await updateField(field.id, payload);
    setField(mapCatalogField(response.field));
    setDatasetName(response.dataset_name);
    setDataSourceName(response.data_source_name);
    setCorrelationId(response.correlation_id);
  }, [field]);

  return (
    <FieldDetailPage
      correlationId={correlationId}
      datasetName={datasetName}
      dataSourceName={dataSourceName}
      field={field}
      onRefresh={() => void load()}
      onUpdateField={handleUpdateField}
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
    <LauncherControlProvider>
      <DevelopmentUserProvider>
        <AppContent />
        <DevelopmentUserSwitcher />
      </DevelopmentUserProvider>
    </LauncherControlProvider>
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
      <Route element={<Navigate replace to="/dashboard" />} path="/" />
      <Route element={<Navigate replace to="/analytics/rule-health" />} path="/analytics" />
      <Route element={<RuleHealthPage />} path="/analytics/rule-health" />
      <Route element={<MetadataHealthPage />} path="/analytics/metadata-health" />
      <Route element={<IssuePerformancePage />} path="/analytics/issues" />
      <Route element={<ScoringPolicyImpactPage />} path="/analytics/scoring-policy" />
      <Route element={<DashboardPage />} path="/dashboard" />
      <Route element={<DataSourcesRoute />} path="/data-sources" />
      <Route element={<CatalogRoute />} path="/catalog" />
      <Route element={<DatasetDetailRoute />} path="/catalog/datasets/:datasetId" />
      <Route element={<FieldDetailRoute />} path="/catalog/fields/:fieldId" />
      <Route element={<RulesRoute />} path="/rules" />
      <Route element={<ExecutionsRoute />} path="/executions" />
      <Route element={<ScoresPage />} path="/scores" />
      <Route element={<ScoreDetailPage />} path="/scores/:scoreId" />
      <Route element={<ScoreComparisonPage />} path="/scores/comparison" />
      <Route element={<DatasetTrendPage />} path="/catalog/datasets/:datasetId/trend" />
      <Route element={<IssuesRoute />} path="/issues" />
      <Route element={<GovernanceTasksRoute />} path="/governance" />
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
