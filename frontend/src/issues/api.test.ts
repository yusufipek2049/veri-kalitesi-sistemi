import { afterEach, describe, expect, it, vi } from "vitest";
import {
  EvidenceApiError,
  fetchInvestigationEvidence,
  fetchIssueAssignmentOptions,
  fetchIssues,
  createIssue,
  IssueApiError,
  reassignIssue,
  resolveIssue,
  startIssueInvestigation,
} from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("issue API istemcisi", () => {
  it("yetkisiz yanıtı güvenli istemci hatasına dönüştürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", {
      status: 403,
      headers: { "X-Correlation-ID": "issue-forbidden" },
    })));

    await expect(fetchIssues()).rejects.toEqual(
      new IssueApiError("unauthorized", "issue-forbidden"),
    );
  });

  it("başarılı yanıtı döndürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({
      api_version: "v1",
      data_origin: "synthetic-test",
      correlation_id: "issue-ok",
      limit: 100,
      items: [],
    })));

    await expect(fetchIssues()).resolves.toMatchObject({ correlation_id: "issue-ok" });
  });

  it("CSRF kanıtı ve sürümle inceleme mutasyonu gönderir", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({
        api_version: "v1",
        data_origin: "test",
        correlation_id: "list",
        limit: 100,
        items: [],
      }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": "memory-only-proof",
        },
      }))
      .mockResolvedValueOnce(Response.json({
        api_version: "v1",
        data_origin: "test",
        correlation_id: "mutation",
        item: {
          issue_id: "issue-a",
          issue_no: "DQI-001",
          source_event_type: "QUALITY",
          trigger_type: "QUALITY_THRESHOLD",
          scope_type: "DATASET",
          scope_id: "dataset-a",
          status: "INVESTIGATING",
          priority: "HIGH",
          occurrence_count: 1,
          version: 2,
          available_actions: [],
          created_at: "2026-07-23T08:00:00Z",
          updated_at: "2026-07-23T09:00:00Z",
          last_seen_at: "2026-07-23T08:00:00Z",
        },
      }));
    vi.stubGlobal("fetch", fetchMock);

    await fetchIssues();
    await startIssueInvestigation("issue-a", 1);

    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/v1/issues/issue-a/investigation",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-CSRF-Token": "memory-only-proof" }),
        body: JSON.stringify({ version: 1 }),
      }),
    );
  });

  it("CSRF kanıtı, idempotency anahtarı ve payload ile yeni sorun oluşturur", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response("{}", {
        status: 200,
        headers: { "X-CSRF-Token": "memory-only-proof" },
      }))
      .mockResolvedValueOnce(Response.json({
        api_version: "v1",
        data_origin: "test",
        correlation_id: "create-ds05",
        item: {
          issue_id: "issue-new-ds05",
          issue_no: "DQI-2026-0200",
          title: "Manuel kalite sorunu",
          source_event_type: "MANUAL",
          trigger_type: "MANUAL",
          scope_type: "DATASET",
          scope_id: "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb",
          status: "NEW",
          priority: "HIGH",
          occurrence_count: 1,
          version: 1,
          source_execution_id: null,
          source_rule_version_id: null,
          available_actions: ["REASSIGN"],
          created_at: "2026-08-05T10:00:00Z",
          updated_at: "2026-08-05T10:00:00Z",
          last_seen_at: "2026-08-05T10:00:00Z",
        },
      }));
    vi.stubGlobal("fetch", fetchMock);
    await fetchIssues();

    const result = await createIssue({
      title: "Manuel kalite sorunu",
      scope_type: "DATASET",
      scope_id: "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb",
      priority: "HIGH",
      idempotency_key: "test-idempotency-key",
    });

    expect(result.correlation_id).toBe("create-ds05");
    expect(result.item.title).toBe("Manuel kalite sorunu");
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/v1/issues",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-CSRF-Token": "memory-only-proof" }),
        body: JSON.stringify({
          title: "Manuel kalite sorunu",
          scope_type: "DATASET",
          scope_id: "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb",
          priority: "HIGH",
          idempotency_key: "test-idempotency-key",
        }),
      }),
    );
  });

  it("createIssue 422 doğrulama hatasında validation hatası verir", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response("{}", {
        status: 200,
        headers: { "X-CSRF-Token": "memory-only-proof" },
      }))
      .mockResolvedValueOnce(new Response("", {
        status: 422,
        headers: { "X-Correlation-ID": "create-validation" },
      }));
    vi.stubGlobal("fetch", fetchMock);
    await fetchIssues();

    await expect(createIssue({
      title: "",
      scope_type: "DATASET",
      scope_id: "ds-1",
      priority: "LOW",
      idempotency_key: "key",
    })).rejects.toEqual(new IssueApiError("validation", "create-validation"));
  });

  it("createIssue 409 çakışma yanıtında conflict hatası verir", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response("{}", {
        status: 200,
        headers: { "X-CSRF-Token": "memory-only-proof" },
      }))
      .mockResolvedValueOnce(new Response("", {
        status: 409,
        headers: { "X-Correlation-ID": "create-conflict" },
      }));
    vi.stubGlobal("fetch", fetchMock);
    await fetchIssues();

    await expect(createIssue({
      title: "Duplikate",
      scope_type: "SOURCE",
      scope_id: "src-1",
      priority: "MEDIUM",
      idempotency_key: "dup-key",
    })).rejects.toEqual(new IssueApiError("conflict", "create-conflict"));
  });

  it("sürüm çakışmasını güvenli conflict hatasına dönüştürür", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response("{}", {
        status: 200,
        headers: { "X-CSRF-Token": "memory-only-proof" },
      }))
      .mockResolvedValueOnce(new Response("", {
        status: 409,
        headers: { "X-Correlation-ID": "issue-conflict" },
      }));
    vi.stubGlobal("fetch", fetchMock);
    await fetchIssues();

    await expect(startIssueInvestigation("issue-a", 1)).rejects.toEqual(
      new IssueApiError("conflict", "issue-conflict"),
    );
  });

  it("atanabilir kullanıcıları veri-minimum endpoint'ten yükler", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({
      api_version: "v1",
      data_origin: "test",
      correlation_id: "options",
      items: [{
        user_id: "4ec96cb4-d150-45d2-9565-c1879d135f08",
        display_name: "Veri Sorumlusu A",
      }],
    }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchIssueAssignmentOptions("issue-a")).resolves.toMatchObject({
      correlation_id: "options",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/issues/issue-a/assignment-options",
      expect.objectContaining({ credentials: "same-origin" }),
    );
  });

  it("CSRF kanıtı, sürüm, kullanıcı ve öncelikle yeniden atama gönderir", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response("{}", {
        status: 200,
        headers: { "X-CSRF-Token": "memory-only-proof" },
      }))
      .mockResolvedValueOnce(Response.json({
        api_version: "v1",
        data_origin: "test",
        correlation_id: "assignment",
        item: {},
      }));
    vi.stubGlobal("fetch", fetchMock);
    await fetchIssues();

    await reassignIssue(
      "issue-a",
      3,
      "4ec96cb4-d150-45d2-9565-c1879d135f08",
      "CRITICAL",
    );

    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/v1/issues/issue-a/assignment",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-CSRF-Token": "memory-only-proof" }),
        body: JSON.stringify({
          version: 3,
          assignee_user_id: "4ec96cb4-d150-45d2-9565-c1879d135f08",
          priority: "CRITICAL",
        }),
      }),
    );
  });

  it("CSRF kanıtı ve sürümle korumalı çözüm kaydı gönderir", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response("{}", {
        status: 200,
        headers: { "X-CSRF-Token": "memory-only-proof" },
      }))
      .mockResolvedValueOnce(Response.json({
        api_version: "v1",
        data_origin: "test",
        correlation_id: "resolution",
        item: {},
      }));
    vi.stubGlobal("fetch", fetchMock);
    await fetchIssues();

    await resolveIssue(
      "issue-a",
      4,
      "Kaynak eşlemesi hatalı",
      "Eşleme yapılandırması düzeltildi",
      "550e8400-e29b-41d4-a716-446655440000",
      "2026-07-23T09:30:00.000Z",
    );

    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/v1/issues/issue-a/resolution",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-CSRF-Token": "memory-only-proof" }),
        body: JSON.stringify({
          version: 4,
          root_cause: "Kaynak eşlemesi hatalı",
          corrective_action: "Eşleme yapılandırması düzeltildi",
          evidence_reference_id: "550e8400-e29b-41d4-a716-446655440000",
          completed_at: "2026-07-23T09:30:00.000Z",
        }),
      }),
    );
  });
});

describe("evidence API istemcisi", () => {
  it("investigation evidence başarılı yanıtı döndürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({
      api_version: "v1",
      data_origin: "synthetic-test",
      correlation_id: "ev-ok",
      issue_id: "issue-1",
      rule_description: { source: "Observed", value: "test", references: ["ref-1"] },
      expected_summary: { source: "Observed", value: "expected", references: [] },
      actual_summary: { source: "Observed", value: "actual", references: [] },
      masked_samples: { source: "Observed", value: ["masked-1"], references: ["fp-1"] },
      similar_history: { source: "Unknown", value: null, references: [] },
      recommendation: { source: "Unknown", value: null, references: [] },
      rule_version_id: "rule-v1",
      ir_version: "ir-v1",
      evidence_fingerprint: "fp-1",
      evidence_query_reference: "qr-1",
      evidence_plan_reference: "pr-1",
      authorization_policy_version: "AUTH_V1",
    })));
    const result = await fetchInvestigationEvidence("issue-1");
    expect(result).toMatchObject({
      correlation_id: "ev-ok",
      issue_id: "issue-1",
    });
    expect(result.rule_description).toMatchObject({ source: "Observed", value: "test" });
  });

  it("investigation evidence 403 yanıtında unauthorized döndürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", {
      status: 403,
      headers: { "X-Correlation-ID": "ev-forbidden" },
    })));
    await expect(fetchInvestigationEvidence("issue-1")).rejects.toEqual(
      new EvidenceApiError("unauthorized", "ev-forbidden"),
    );
  });
});
