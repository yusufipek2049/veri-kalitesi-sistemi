export type DataSourceState = "normal" | "loading" | "empty" | "error" | "unauthorized" | "long-content";

export interface DataSourceListItem {
  id: string;
  name: string;
  sourceType: string;
  status: string;
  lastTestAt?: string;
}

export interface DataSourceListApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  items: Array<{
    data_source_id: string;
    name: string;
    source_type: string;
    status: string;
    last_test_at: string | null;
  }>;
}

export const syntheticDataSources: DataSourceListItem[] = [
  { id: "source-core-banking", name: "Temel Bankacılık", sourceType: "POSTGRESQL", status: "ACTIVE", lastTestAt: "2026-07-22T08:30:00Z" },
  { id: "source-customer-file", name: "Müşteri Dosyaları", sourceType: "CSV", status: "TEST_SUCCEEDED", lastTestAt: "2026-07-21T14:10:00Z" },
  { id: "source-risk-mart", name: "Risk Veri Martı", sourceType: "MSSQL", status: "INACTIVE", lastTestAt: "2026-07-18T11:45:00Z" },
  { id: "source-regulatory-api", name: "Düzenleyici Veri Servisi", sourceType: "REST", status: "TEST_FAILED", lastTestAt: "2026-07-22T07:05:00Z" },
];

export function dataSourcesFromApi(response: DataSourceListApiResponse): DataSourceListItem[] {
  return response.items.map((item) => ({
    id: item.data_source_id,
    name: item.name,
    sourceType: item.source_type,
    status: item.status,
    lastTestAt: item.last_test_at ?? undefined,
  }));
}
