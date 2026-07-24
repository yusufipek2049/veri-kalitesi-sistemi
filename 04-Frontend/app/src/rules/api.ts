import type {
  RuleApprovalDecisionRequest,
  RuleApprovalRequestPayload,
  RuleApprovalWithdrawRequest,
  RuleCreateRequest,
  RuleListApiResponse,
  RuleMutationApiResponse,
  RuleTestRequest,
  RuleTestResult,
  RuleVersionCreateRequest,
} from "./model";

const CSRF_HEADER = "X-CSRF-Token";
let csrfProof: string | undefined;

export class RuleApiError extends Error {
  constructor(
    public readonly kind: "unauthorized" | "conflict" | "validation" | "technical",
    public readonly correlationId?: string,
  ) {
    super(
      correlationId
        ? `İşlem tamamlanamadı. Yeniden deneyin. İzleme kodu: ${correlationId}.`
        : "İşlem tamamlanamadı. Yeniden deneyin.",
    );
  }
}

function ruleApiError(response: Response): RuleApiError {
  const correlationId = response.headers.get("X-Correlation-ID") ?? undefined;
  const kind = response.status === 401 || response.status === 403
    ? "unauthorized"
    : response.status === 409
      ? "conflict"
      : response.status === 422
        ? "validation"
        : "technical";
  return new RuleApiError(kind, correlationId);
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
  const receivedProof = response.headers.get(CSRF_HEADER);
  if (receivedProof) csrfProof = receivedProof;
  return response.json() as Promise<RuleListApiResponse>;
}

export async function createRule(
  payload: RuleCreateRequest,
): Promise<RuleMutationApiResponse> {
  if (!csrfProof) throw new RuleApiError("unauthorized");
  const response = await fetch("/api/v1/rules", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      [CSRF_HEADER]: csrfProof,
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw ruleApiError(response);
  return response.json() as Promise<RuleMutationApiResponse>;
}

export async function createRuleVersion(
  qualityRuleId: string,
  payload: RuleVersionCreateRequest,
): Promise<RuleMutationApiResponse> {
  if (!csrfProof) throw new RuleApiError("unauthorized");
  const response = await fetch(
    `/api/v1/rules/${encodeURIComponent(qualityRuleId)}/versions`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        [CSRF_HEADER]: csrfProof,
      },
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) throw ruleApiError(response);
  return response.json() as Promise<RuleMutationApiResponse>;
}

export async function testRule(
  qualityRuleId: string,
  payload: RuleTestRequest,
): Promise<RuleTestResult> {
  if (!csrfProof) throw new RuleApiError("unauthorized");
  const response = await fetch(
    `/api/v1/rules/${encodeURIComponent(qualityRuleId)}/test`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        [CSRF_HEADER]: csrfProof,
      },
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) throw ruleApiError(response);
  return response.json() as Promise<RuleTestResult>;
}

export async function activateRule(
  qualityRuleId: string,
): Promise<RuleMutationApiResponse> {
  if (!csrfProof) throw new RuleApiError("unauthorized");
  const response = await fetch(
    `/api/v1/rules/${encodeURIComponent(qualityRuleId)}/activation`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        [CSRF_HEADER]: csrfProof,
      },
      body: JSON.stringify({ quality_rule_id: qualityRuleId }),
    },
  );
  if (!response.ok) throw ruleApiError(response);
  return response.json() as Promise<RuleMutationApiResponse>;
}

export async function requestRuleApproval(
  qualityRuleId: string,
): Promise<RuleMutationApiResponse> {
  if (!csrfProof) throw new RuleApiError("unauthorized");
  const response = await fetch(
    `/api/v1/rules/${encodeURIComponent(qualityRuleId)}/approval`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        [CSRF_HEADER]: csrfProof,
      },
      body: JSON.stringify({ quality_rule_id: qualityRuleId } satisfies RuleApprovalRequestPayload),
    },
  );
  if (!response.ok) throw ruleApiError(response);
  return response.json() as Promise<RuleMutationApiResponse>;
}

export async function decideRuleApproval(
  approvalRequestId: string,
  payload: RuleApprovalDecisionRequest,
): Promise<RuleMutationApiResponse> {
  if (!csrfProof) throw new RuleApiError("unauthorized");
  const response = await fetch(
    `/api/v1/rules/approval/${encodeURIComponent(approvalRequestId)}/decide`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        [CSRF_HEADER]: csrfProof,
      },
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) throw ruleApiError(response);
  return response.json() as Promise<RuleMutationApiResponse>;
}

export async function withdrawRuleApproval(
  approvalRequestId: string,
  payload: RuleApprovalWithdrawRequest,
): Promise<RuleMutationApiResponse> {
  if (!csrfProof) throw new RuleApiError("unauthorized");
  const response = await fetch(
    `/api/v1/rules/approval/${encodeURIComponent(approvalRequestId)}/withdraw`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        [CSRF_HEADER]: csrfProof,
      },
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) throw ruleApiError(response);
  return response.json() as Promise<RuleMutationApiResponse>;
}

export async function passivateRule(
  qualityRuleId: string,
): Promise<RuleMutationApiResponse> {
  if (!csrfProof) throw new RuleApiError("unauthorized");
  const response = await fetch(
    `/api/v1/rules/${encodeURIComponent(qualityRuleId)}/passivation`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        [CSRF_HEADER]: csrfProof,
      },
      body: JSON.stringify({ quality_rule_id: qualityRuleId }),
    },
  );
  if (!response.ok) throw ruleApiError(response);
  return response.json() as Promise<RuleMutationApiResponse>;
}