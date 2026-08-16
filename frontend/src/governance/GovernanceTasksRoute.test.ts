import { describe, expect, it } from "vitest";
import { canCreateGovernanceRequest } from "./GovernanceTasksRoute";
import {
  filterGovernanceOwnerCandidates,
} from "./GovernanceTasksPage";

describe("yönetişim talebi oluşturma yetkisi", () => {
  it.each([
    "DATA_STEWARD",
    "DATA_VIEWER / DATA_STEWARD",
    "DATA_VIEWER / DATA_GOVERNANCE_SPECIALIST",
  ])("maker rolü için oluşturma aksiyonunu açar: %s", (roles) => {
    expect(canCreateGovernanceRequest(roles)).toBe(true);
  });

  it.each([undefined, "", "DATA_VIEWER", "DATA_VIEWER / DATA_OWNER", "DATA_ENGINEER"])(
    "maker olmayan rol için oluşturma aksiyonunu kapatır: %s",
    (roles) => {
      expect(canCreateGovernanceRequest(roles)).toBe(false);
    },
  );
});

describe("yeni sahip araması", () => {
  const candidates = [
    { id: "dev-data-owner", displayName: "Data Owner", roles: "DATA_OWNER" },
    { id: "dev-data-steward", displayName: "Data Steward", roles: "DATA_STEWARD" },
    { id: "dev-data-engineer", displayName: "Veri Mühendisi", roles: "DATA_ENGINEER" },
    { id: "dev-data-governance", displayName: "Veri Yönetişim Uzmanı", roles: "DATA_GOVERNANCE_SPECIALIST" },
    { id: "dev-audit-viewer", displayName: "Denetim Görüntüleyici", roles: "AUDIT_VIEWER" },
    { id: "dev-data-viewer", displayName: "Veri Görüntüleyici", roles: "DATA_VIEWER" },
  ];

  it("kimlik, görünen ad ve rol metnine göre filtreler", () => {
    expect(filterGovernanceOwnerCandidates(candidates, "governance").map((item) => item.id)).toEqual([
      "dev-data-governance",
    ]);
    expect(filterGovernanceOwnerCandidates(candidates, "mühendisi").map((item) => item.id)).toEqual([
      "dev-data-engineer",
    ]);
    expect(filterGovernanceOwnerCandidates(candidates, "audit_viewer").map((item) => item.id)).toEqual([
      "dev-audit-viewer",
    ]);
  });

  it("başlangıç eşleşmesini öne alır ve sonucu beşle sınırlar", () => {
    const result = filterGovernanceOwnerCandidates(candidates, "data");
    expect(result).toHaveLength(5);
    expect(result[0].displayName).toBe("Data Owner");
  });
});
