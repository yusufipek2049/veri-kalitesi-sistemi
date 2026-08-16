type DiscoveryLifecycleStatus =
  | "QUEUED"
  | "RUNNING"
  | "SUCCESS"
  | "PARTIAL"
  | "TECHNICAL_ERROR"
  | "CANCELLED";

type DiffStatus = "PENDING" | "APPLIED";
export type CatalogItemStatus = "ACTIVE" | "INACTIVE";

export type CatalogPageState = "normal" | "loading" | "empty" | "error" | "unauthorized";
export type DatasetDetailState = "normal" | "loading" | "error" | "unauthorized" | "not-found";
export type FieldDetailState = "normal" | "loading" | "error" | "unauthorized" | "not-found";

export interface CatalogDataset {
  id: string;
  dataSourceId: string;
  namespace: string;
  name: string;
  datasetType: string;
  status: CatalogItemStatus;
  estimatedRowCount: number | null;
  fieldCount: number;
  version: number;
  ownerId: string | null;
}

export interface CatalogField {
  id: string;
  datasetId: string;
  name: string;
  nativeDataType: string;
  isNullable: boolean;
  isSensitive: boolean;
  classification: string;
  status: CatalogItemStatus;
  version: number;
}

export interface DiscoveryStatus {
  discoveryId: number;
  dataSourceId: string;
  status: DiscoveryLifecycleStatus;
  scannedObjectCount: number;
  completedScope: Record<string, unknown>;
  partialReasonCode: string | null;
  startedAt: string | null;
  finishedAt: string | null;
  correlationId: string | null;
}

export interface MetadataDiff {
  metadataDiffId: string | null;
  discoveryId: number;
  dataSourceId: string;
  status: DiffStatus;
  addedObjects: Record<string, unknown>[];
  changedObjects: Record<string, unknown>[];
  removedObjects: Record<string, unknown>[];
  requiresRuleReview: boolean;
}

export interface DiscoveryScope {
  dataSourceId: string;
  includePatterns: string[];
  excludePatterns: string[];
  pageSize: number;
  maxObjects: number;
  timeoutSeconds: number;
  version: number;
}

// ── API response contracts ──────────────────────────────────────────

interface ApiEnvelope {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
}

export interface CatalogDatasetListApiResponse extends ApiEnvelope {
  items: {
    dataset_id: string;
    data_source_id: string;
    namespace: string;
    name: string;
    dataset_type: string;
    status: CatalogItemStatus;
    estimated_row_count: number | null;
    field_count: number;
    version: number;
    owner_user_id?: string | null;
  }[];
}

export interface CatalogDatasetDetailApiResponse extends ApiEnvelope {
  dataset: CatalogDatasetListApiResponse["items"][number];
  data_source_name: string;
}

export interface CatalogFieldListApiResponse extends ApiEnvelope {
  items: {
    data_field_id: string;
    dataset_id: string;
    name: string;
    native_data_type: string;
    is_nullable: boolean;
    is_sensitive: boolean;
    classification: string;
    status: CatalogItemStatus;
    version: number;
  }[];
}

export interface CatalogFieldDetailApiResponse extends ApiEnvelope {
  field: CatalogFieldListApiResponse["items"][number];
  dataset_name: string;
  data_source_name: string;
}

export interface DiscoveryStatusApiResponse extends ApiEnvelope {
  discovery_id: number;
  data_source_id: string;
  status: DiscoveryLifecycleStatus;
  scanned_object_count: number;
  completed_scope: Record<string, unknown>;
  partial_reason_code: string | null;
  started_at: string | null;
  finished_at: string | null;
  discovery_correlation_id: string | null;
}

export interface DiscoveryDiffApiResponse extends ApiEnvelope {
  metadata_diff_id: string | null;
  discovery_id: number;
  data_source_id: string;
  status: DiffStatus;
  added_objects: Record<string, unknown>[];
  changed_objects: Record<string, unknown>[];
  removed_objects: Record<string, unknown>[];
  requires_rule_review: boolean;
}

export interface DiscoveryResponse extends ApiEnvelope {
  discovery_id: number;
  data_source_id: string;
  status: string;
  job_id: string | null;
}

export interface DiscoveryScopeApiResponse extends ApiEnvelope {
  data_source_id: string;
  include_patterns: string[];
  exclude_patterns: string[];
  page_size: number;
  max_objects: number;
  timeout_seconds: number;
  version: number;
}

export interface DiffApplicationApiResponse extends ApiEnvelope {
  metadata_diff_id: string;
  status: string;
  applied_at: string | null;
}

// ── Mappers ─────────────────────────────────────────────────────────

export function mapCatalogDataset(api: CatalogDatasetListApiResponse["items"][number]): CatalogDataset {
  return {
    id: api.dataset_id,
    dataSourceId: api.data_source_id,
    namespace: api.namespace,
    name: api.name,
    datasetType: api.dataset_type,
    status: api.status,
    estimatedRowCount: api.estimated_row_count,
    fieldCount: api.field_count,
    version: api.version,
    ownerId: api.owner_user_id ?? null,
  };
}

export function mapCatalogField(api: CatalogFieldListApiResponse["items"][number]): CatalogField {
  return {
    id: api.data_field_id,
    datasetId: api.dataset_id,
    name: api.name,
    nativeDataType: api.native_data_type,
    isNullable: api.is_nullable,
    isSensitive: api.is_sensitive,
    classification: api.classification,
    status: api.status,
    version: api.version,
  };
}

export function mapDiscoveryStatus(api: DiscoveryStatusApiResponse): DiscoveryStatus {
  return {
    discoveryId: api.discovery_id,
    dataSourceId: api.data_source_id,
    status: api.status,
    scannedObjectCount: api.scanned_object_count,
    completedScope: api.completed_scope,
    partialReasonCode: api.partial_reason_code,
    startedAt: api.started_at,
    finishedAt: api.finished_at,
    correlationId: api.discovery_correlation_id,
  };
}

export function mapMetadataDiff(api: DiscoveryDiffApiResponse): MetadataDiff {
  return {
    metadataDiffId: api.metadata_diff_id,
    discoveryId: api.discovery_id,
    dataSourceId: api.data_source_id,
    status: api.status,
    addedObjects: api.added_objects,
    changedObjects: api.changed_objects,
    removedObjects: api.removed_objects,
    requiresRuleReview: api.requires_rule_review,
  };
}

export function mapDiscoveryScope(api: DiscoveryScopeApiResponse): DiscoveryScope {
  return {
    dataSourceId: api.data_source_id,
    includePatterns: api.include_patterns,
    excludePatterns: api.exclude_patterns,
    pageSize: api.page_size,
    maxObjects: api.max_objects,
    timeoutSeconds: api.timeout_seconds,
    version: api.version,
  };
}

// ── Update request types ────────────────────────────────────────────

export interface DatasetUpdatePayload {
  name?: string;
  namespace?: string;
  status?: CatalogItemStatus;
  expected_version?: number;
}

export interface FieldUpdatePayload {
  native_data_type?: string;
  is_nullable?: boolean;
  is_sensitive?: boolean;
  classification?: string;
  status?: CatalogItemStatus;
  expected_version?: number;
}

export const CLASSIFICATION_OPTIONS: readonly string[] = [
  "UNCLASSIFIED",
  "PUBLIC",
  "INTERNAL",
  "CONFIDENTIAL",
  "RESTRICTED",
  "PERSONAL_DATA",
  "SPECIAL_CATEGORY_PERSONAL_DATA",
  "CUSTOMER_SECRET",
  "BANK_SECRET",
] as const;
