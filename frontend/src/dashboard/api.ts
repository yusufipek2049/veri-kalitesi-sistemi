import type { DashboardOverviewApiResponse } from "./model";
import { developmentFetch } from "../development/fetch";

export type DashboardErrorKind =
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "validation"
  | "technical";

export class DashboardApiError extends Error {
  constructor(
    public readonly kind: DashboardErrorKind,
    public readonly correlationId?: string,
  ) {
    super("Dashboard request failed.");
  }
}

export interface DashboardOverviewParams {
  scopeType?: "SOURCE" | "ENTERPRISE";
  scopeId?: string;
  startDate?: string;
  endDate?: string;
}

function classifyStatus(status: number): DashboardErrorKind {
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 404) return "not_found";
  if (status === 400 || status === 422) return "validation";
  return "technical";
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new DashboardApiError(classifyStatus(response.status), correlationId);
  }
  return response.json() as Promise<T>;
}

export async function fetchDashboardOverview(
  params: DashboardOverviewParams = {},
  signal?: AbortSignal,
): Promise<DashboardOverviewApiResponse> {
  const searchParams = new URLSearchParams();
  if (params.scopeType) searchParams.set("scope_type", params.scopeType);
  if (params.scopeId) searchParams.set("scope_id", params.scopeId);
  if (params.startDate) searchParams.set("start_date", params.startDate);
  if (params.endDate) searchParams.set("end_date", params.endDate);
  const query = searchParams.toString();
  const response = await developmentFetch(
    `/api/v1/dashboard/overview${query ? `?${query}` : ""}`,
    {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
    },
  );
  return handleResponse<DashboardOverviewApiResponse>(response);
}
