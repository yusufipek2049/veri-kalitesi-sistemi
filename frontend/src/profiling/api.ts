import type {
  DriftJudgmentApiResponse,
  ProfileSnapshotDetailApiResponse,
  ProfileSnapshotListApiResponse,
} from "./model";
import { developmentFetch } from "../development/fetch";

export class ProfilingApiError extends Error {
  constructor(
    public readonly kind: "unauthorized" | "not-found" | "technical",
    public readonly correlationId?: string,
  ) {
    super(
      correlationId
        ? `Profil verileri alınamadı. İzleme kodu: ${correlationId}.`
        : "Profil verileri alınamadı.",
    );
  }
}

export async function fetchProfileSnapshots(
  datasetId: string,
  signal?: AbortSignal,
): Promise<ProfileSnapshotListApiResponse> {
  const params = new URLSearchParams({ dataset_id: datasetId });
  const response = await developmentFetch(`/api/v1/profile-snapshots?${params}`, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new ProfilingApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      correlationId,
    );
  }
  return response.json() as Promise<ProfileSnapshotListApiResponse>;
}

export async function fetchProfileSnapshotDetail(
  profileId: string,
  signal?: AbortSignal,
): Promise<ProfileSnapshotDetailApiResponse> {
  const response = await developmentFetch(
    `/api/v1/profile-snapshots/${encodeURIComponent(profileId)}`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new ProfilingApiError(
      response.status === 401 || response.status === 403
        ? "unauthorized"
        : response.status === 404
          ? "not-found"
          : "technical",
      correlationId,
    );
  }
  return response.json() as Promise<ProfileSnapshotDetailApiResponse>;
}

export async function fetchDriftJudgment(
  profileId: string,
  baselineProfileId?: string,
  signal?: AbortSignal,
): Promise<DriftJudgmentApiResponse> {
  const params = new URLSearchParams();
  if (baselineProfileId) params.set("baseline_profile_id", baselineProfileId);
  const query = params.toString() ? `?${params}` : "";
  const response = await developmentFetch(
    `/api/v1/profile-snapshots/${encodeURIComponent(profileId)}/drift${query}`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new ProfilingApiError(
      response.status === 401 || response.status === 403
        ? "unauthorized"
        : response.status === 404
          ? "not-found"
          : "technical",
      correlationId,
    );
  }
  return response.json() as Promise<DriftJudgmentApiResponse>;
}
