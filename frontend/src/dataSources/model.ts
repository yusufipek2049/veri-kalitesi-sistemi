export type DataSourceState = "normal" | "loading" | "empty" | "error" | "unauthorized" | "long-content";

export type DataSourceAction =
  | "TEST_CONNECTION"
  | "REQUEST_ACTIVATION"
  | "APPROVE_ACTIVATION"
  | "REJECT_ACTIVATION"
  | "PASSIVATE"
  | "DISCOVER_METADATA";

export interface DataSourceListItem {
  id: string;
  name: string;
  sourceType: string;
  status: string;
  lastTestAt?: string;
  availableActions: DataSourceAction[];
  pendingActivationRequestId?: string;
  pendingActivationMakerActorId?: string;
  pendingActivationRequestedAt?: string;
  pendingActivationExpiresAt?: string;
}

export interface DataSourceApiItem {
  data_source_id: string;
  name: string;
  source_type: string;
  status: string;
  last_test_at: string | null;
  available_actions: DataSourceAction[];
  pending_activation_request_id: string | null;
  pending_activation_maker_actor_id: string | null;
  pending_activation_requested_at: string | null;
  pending_activation_expires_at: string | null;
}

export interface DataSourceListApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  items: DataSourceApiItem[];
}

export interface DataSourceCreateRequest {
  name: string;
  source_type: "POSTGRESQL";
  host: string;
  port: number;
  database: string;
  schema: string;
  secret_reference: string;
  ssl_mode: "require" | "verify-ca" | "verify-full";
  connect_timeout_seconds: number;
  statement_timeout_ms: number;
  connection_parameters?: Record<string, unknown>;
}

export interface DataSourceMutationApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: DataSourceApiItem;
  activation_request_status: string | null;
  replayed: boolean;
}

export const syntheticDataSources: DataSourceListItem[] = [
  {
    id: "source-core-banking",
    name: "Temel Bankacılık",
    sourceType: "POSTGRESQL",
    status: "ACTIVE",
    lastTestAt: "2026-07-22T08:30:00Z",
    availableActions: ["PASSIVATE", "DISCOVER_METADATA"],
  },
  {
    id: "source-customer-file",
    name: "Müşteri Dosyaları",
    sourceType: "CSV",
    status: "TEST_SUCCEEDED",
    lastTestAt: "2026-07-21T14:10:00Z",
    availableActions: ["TEST_CONNECTION", "REQUEST_ACTIVATION"],
  },
  {
    id: "source-risk-mart",
    name: "Risk Veri Martı",
    sourceType: "MSSQL",
    status: "INACTIVE",
    lastTestAt: "2026-07-18T11:45:00Z",
    availableActions: ["TEST_CONNECTION"],
  },
  {
    id: "source-regulatory-api",
    name: "Düzenleyici Veri Servisi",
    sourceType: "REST",
    status: "TEST_FAILED",
    lastTestAt: "2026-07-22T07:05:00Z",
    availableActions: ["TEST_CONNECTION"],
  },
];

export function dataSourceFromApi(item: DataSourceApiItem): DataSourceListItem {
  return {
    id: item.data_source_id,
    name: item.name,
    sourceType: item.source_type,
    status: item.status,
    lastTestAt: item.last_test_at ?? undefined,
    availableActions: item.available_actions,
    pendingActivationRequestId: item.pending_activation_request_id ?? undefined,
    pendingActivationMakerActorId: item.pending_activation_maker_actor_id ?? undefined,
    pendingActivationRequestedAt: item.pending_activation_requested_at ?? undefined,
    pendingActivationExpiresAt: item.pending_activation_expires_at ?? undefined,
  };
}

export function dataSourcesFromApi(response: DataSourceListApiResponse): DataSourceListItem[] {
  return response.items.map(dataSourceFromApi);
}
