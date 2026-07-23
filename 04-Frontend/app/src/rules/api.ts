import type { RuleCreateRequest, RuleListApiResponse, RuleMutationApiResponse } from "./model";

export class RuleApiError extends Error {
  constructor(
    public readonly kind: "unauthorized" | "technical" | "validation",
    public readonly correlationId?: string,
  ) {
    super("Rule list request failed.");
  }
}

export async function fetchRules(signal?: AbortSignal): Promise<RuleListApiResponse> {
  const response = await fetch("/api/v1/rules", {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new RuleApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      correlationId,
    );
  }
  return response.json() as Promise<RuleListApiResponse>;
}

export async function createRule(
  payload: RuleCreateRequest,
  csrfProof?: string,
): Promise<RuleMutationApiResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (csrfProof) {
    headers["X-CSRF-Proof"] = csrfProof;
  }
  const response = await fetch("/api/v1/rules", {
    method: "POST",
    credentials: "same-origin",
    headers,
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
    throw new RuleApiError(
      response.status === 401 || response.status === 403 ? "unauthorized" : "technical",
      correlationId,
    );
  }
  return response.json() as Promise<RuleMutationApiResponse>;
}
