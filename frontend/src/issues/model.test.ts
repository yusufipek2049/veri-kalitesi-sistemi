import { describe, expect, it } from "vitest";
import {
  assigneeOptionsFromApi,
  evidenceComponentValueText,
  governanceProjectionFromApi,
  investigationEvidenceFromApi,
  isHypothesisSnapshotKind,
  issuesFromApi,
  lineageSnapshotFromApi,
  sourceClassLabel,
} from "./model";

describe("issue API modeli", () => {
  it("snake_case yanıtı istemci modeline dönüştürür", () => {
    const [issue] = issuesFromApi({
      api_version: "v1",
      data_origin: "synthetic-test",
      correlation_id: "issue-model-test",
      limit: 100,
      available_actions: [],
      items: [{
        issue_id: "issue-a",
        issue_no: "DQI-001",
        title: "Test issue",
        source_event_type: "TECHNICAL",
        trigger_type: "TECHNICAL_ERROR",
        scope_type: "SOURCE",
        scope_id: "source-a",
        status: "ASSIGNED",
        priority: "HIGH",
        occurrence_count: 3,
        version: 4,
        source_execution_id: null,
        source_rule_version_id: null,
        available_actions: ["START_INVESTIGATION"],
        created_at: "2026-07-23T08:00:00Z",
        updated_at: "2026-07-23T09:00:00Z",
        last_seen_at: "2026-07-23T09:00:00Z",
      }],
    });

    expect(issue).toMatchObject({
      id: "issue-a",
      issueNo: "DQI-001",
      sourceEventType: "TECHNICAL",
      occurrenceCount: 3,
      version: 4,
      availableActions: ["START_INVESTIGATION"],
    });
  });

  it("atanabilir kullanıcı seçeneğini güvenli istemci modeline dönüştürür", () => {
    expect(assigneeOptionsFromApi({
      api_version: "v1",
      data_origin: "synthetic-test",
      correlation_id: "assignee-options",
      items: [{
        user_id: "4ec96cb4-d150-45d2-9565-c1879d135f08",
        display_name: "Veri Sorumlusu A",
      }],
    })).toEqual([{
      userId: "4ec96cb4-d150-45d2-9565-c1879d135f08",
      displayName: "Veri Sorumlusu A",
    }]);
  });
});

describe("DS-05: title, source refs ve page-level available_actions", () => {
  it("issue API yanıtındaki title, source_execution_id ve source_rule_version_id alanlarını dönüştürür", () => {
    const [issue] = issuesFromApi({
      api_version: "v1",
      data_origin: "synthetic-test",
      correlation_id: "ds05-model",
      limit: 100,
      available_actions: ["CREATE_ISSUE"],
      items: [{
        issue_id: "issue-ds05",
        issue_no: "DQI-2026-0100",
        title: "Manuel kalite sorunu",
        source_event_type: "MANUAL",
        trigger_type: "MANUAL",
        scope_type: "DATASET",
        scope_id: "dataset-customer",
        status: "NEW",
        priority: "MEDIUM",
        occurrence_count: 1,
        version: 1,
        source_execution_id: "exec-ds05",
        source_rule_version_id: "rv-ds05",
        available_actions: ["REASSIGN"],
        created_at: "2026-08-05T10:00:00Z",
        updated_at: "2026-08-05T10:00:00Z",
        last_seen_at: "2026-08-05T10:00:00Z",
      }],
    });

    expect(issue.title).toBe("Manuel kalite sorunu");
    expect(issue.sourceExecutionId).toBe("exec-ds05");
    expect(issue.sourceRuleVersionId).toBe("rv-ds05");
  });

  it("null source refs alanlarını null olarak eşler", () => {
    const [issue] = issuesFromApi({
      api_version: "v1",
      data_origin: "synthetic-test",
      correlation_id: "ds05-null",
      limit: 100,
      available_actions: [],
      items: [{
        issue_id: "issue-null-refs",
        issue_no: "DQI-2026-0101",
        title: "",
        source_event_type: "TECHNICAL",
        trigger_type: "TECHNICAL_ERROR",
        scope_type: "SOURCE",
        scope_id: "source-x",
        status: "NEW",
        priority: "HIGH",
        occurrence_count: 1,
        version: 1,
        source_execution_id: null,
        source_rule_version_id: null,
        available_actions: [],
        created_at: "2026-08-05T10:00:00Z",
        updated_at: "2026-08-05T10:00:00Z",
        last_seen_at: "2026-08-05T10:00:00Z",
      }],
    });

    expect(issue.title).toBe("");
    expect(issue.sourceExecutionId).toBeNull();
    expect(issue.sourceRuleVersionId).toBeNull();
  });
});

describe("evidence investigation modeli", () => {
  it("lineage snapshot yanıtını istemci modeline dönüştürür", () => {
    const snapshot = lineageSnapshotFromApi({
      api_version: "v1",
      data_origin: "synthetic-test",
      correlation_id: "snap-1",
      snapshot_id: "snap-abc",
      snapshot_kind: "LINEAGE_EVENTS",
      subject_ref: "source-customer",
      version_label: "v3",
      digest: "sha256:abc123",
      created_at: "2026-08-01T10:00:00Z",
      payload: { events: [] },
    });
    expect(snapshot).toMatchObject({
      snapshotId: "snap-abc",
      snapshotKind: "LINEAGE_EVENTS",
      subjectRef: "source-customer",
      versionLabel: "v3",
      digest: "sha256:abc123",
    });
  });

  it("yönetişim projeksiyonunu istemci modeline dönüştürür", () => {
    const projection = governanceProjectionFromApi({
      api_version: "v1",
      data_origin: "synthetic-test",
      correlation_id: "gov-1",
      asset_ref: "source-customer",
      governance_profile_status: "ACTIVE",
      governance_reason_codes: [],
      governance_version: "GP_V1:source-customer:2",
      governance_asset_ref: "source-customer",
      critical_asset_status: "Observed",
      risk_status: "Calculated",
      sla_status: "UNKNOWN",
    });
    expect(projection).toMatchObject({
      assetRef: "source-customer",
      governanceProfileStatus: "ACTIVE",
      criticalAssetStatus: "Observed",
      riskStatus: "Calculated",
      slaStatus: "Unknown",
    });
  });

  it("geçersiz kaynak sınıflandırmasını Unknown'a çeker", () => {
    const projection = governanceProjectionFromApi({
      api_version: "v1",
      data_origin: "test",
      correlation_id: "gov-2",
      asset_ref: "source-x",
      governance_profile_status: "NO_ACTIVE_PROFILE",
      governance_reason_codes: ["MISSING_CRITICALITY"],
      governance_version: null,
      governance_asset_ref: null,
      critical_asset_status: "INVALID_TOKEN",
      risk_status: "",
      sla_status: "Estimated",
    });
    expect(projection.criticalAssetStatus).toBe("Unknown");
    expect(projection.riskStatus).toBe("Unknown");
    expect(projection.slaStatus).toBe("Estimated");
  });

  it("ROOT_CAUSE_HYPOTHESIS hipotez olarak işaretlenir", () => {
    expect(isHypothesisSnapshotKind("ROOT_CAUSE_HYPOTHESIS")).toBe(true);
    expect(isHypothesisSnapshotKind("LINEAGE_EVENTS")).toBe(false);
  });

  it("kaynak sınıflandırması etiketleri Türkçe'dir", () => {
    expect(sourceClassLabel("Observed")).toBe("Gözlemlenen");
    expect(sourceClassLabel("Unknown")).toBe("Bilinmeyen");
  });
});

describe("investigation evidence modeli", () => {
  const baseComponent = {
    source: "Observed",
    value: "test",
    references: ["ref-1"] as readonly string[],
  };

  function mockApiResponse(overrides?: Record<string, unknown>) {
    return {
      api_version: "v1" as const,
      data_origin: "synthetic-test",
      correlation_id: "ev-1",
      issue_id: "issue-1",
      rule_description: baseComponent,
      expected_summary: baseComponent,
      actual_summary: baseComponent,
      masked_samples: { source: "Observed", value: ["masked-1"], references: ["fp-1"] as readonly string[] },
      similar_history: { source: "Unknown", value: null, references: [] as readonly string[] },
      recommendation: { source: "Unknown", value: null, references: [] as readonly string[] },
      rule_version_id: "rule-v1",
      ir_version: "ir-v1",
      evidence_fingerprint: "fp-1",
      evidence_query_reference: "qr-1",
      evidence_plan_reference: "pr-1",
      authorization_policy_version: "AUTH_V1",
      ...overrides,
    };
  }

  it("investigation evidence API yanıtını istemci modeline dönüştürür", () => {
    const evidence = investigationEvidenceFromApi(mockApiResponse());
    expect(evidence).toMatchObject({
      issueId: "issue-1",
      ruleVersionId: "rule-v1",
      irVersion: "ir-v1",
      evidenceFingerprint: "fp-1",
      authorizationPolicyVersion: "AUTH_V1",
    });
    expect(evidence.ruleDescription.source).toBe("Observed");
    expect(evidence.similarHistory.source).toBe("Unknown");
    expect(evidence.recommendation.source).toBe("Unknown");
  });

  it("geçersiz kaynak sınıflandırmasını Unknown'a çeker", () => {
    const evidence = investigationEvidenceFromApi(mockApiResponse({
      rule_description: { source: "INVALID", value: "x", references: [] },
    }));
    expect(evidence.ruleDescription.source).toBe("Unknown");
  });

  it("references'ı readonly'den mutable'a dönüştürür", () => {
    const evidence = investigationEvidenceFromApi(mockApiResponse());
    expect(Array.isArray(evidence.ruleDescription.references)).toBe(true);
    expect(evidence.ruleDescription.references).toEqual(["ref-1"]);
  });
});

describe("evidenceComponentValueText", () => {
  it("string değeri doğrudan döndürür", () => {
    expect(evidenceComponentValueText({ source: "Observed", value: "hello", references: [] })).toBe("hello");
  });

  it("array değeri satır satır birleştirir", () => {
    expect(evidenceComponentValueText({ source: "Observed", value: ["a", "b", "c"], references: [] })).toBe("a\nb\nc");
  });

  it("object değeri JSON olarak biçimlendirir", () => {
    const result = evidenceComponentValueText({ source: "Observed", value: { key: "val" }, references: [] });
    expect(result).toContain('"key"');
    expect(result).toContain('"val"');
  });

  it("null değerde boş string döndürür", () => {
    expect(evidenceComponentValueText({ source: "Unknown", value: null, references: [] })).toBe("");
  });
});
