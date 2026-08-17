/** Geliştirme modu kullanıcı API'si. */


export interface DevelopmentUserInfo {
  user_id: string;
  display_name: string;
  roles: string;
  /** Audit kayıtlarındaki aktör kimliği; eski yanıtlarda bulunmayabilir. */
  actor_id?: string;
}

export interface DevelopmentUserListResponse {
  items: DevelopmentUserInfo[];
}

class DevelopmentUserApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly correlationId?: string,
  ) {
    super(message);
    this.name = "DevelopmentUserApiError";
  }
}

export async function fetchDevelopmentUsers(
  signal?: AbortSignal,
): Promise<DevelopmentUserListResponse> {
  const response = await fetch("/api/v1/development/users", {
    credentials: "include",
    signal,
  });
  if (!response.ok) {
    throw new DevelopmentUserApiError(
      "Failed to fetch development users",
      response.status,
      response.headers.get("X-Correlation-ID") ?? undefined,
    );
  }
  return response.json() as Promise<DevelopmentUserListResponse>;
}