import { expect, test } from "@playwright/test";

const viewports = [
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1280x800", width: 1280, height: 800 },
  { name: "1024x768", width: 1024, height: 768 },
  { name: "1366x768", width: 1366, height: 768 },
  { name: "1920x1080", width: 1920, height: 1080 },
];

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.route("**/api/v1/rules", async (route) => {
    await route.fulfill({
      body: JSON.stringify(ruleFixture()),
      contentType: "application/json",
      headers: { "X-Correlation-ID": "e2e-rules" },
      status: 200,
    });
  });
});

for (const viewport of viewports) {
  for (const colorMode of ["light", "dark"] as const) {
    test(`kurallar ${viewport.name} ${colorMode} görünümünde taşma üretmez`, async ({ page }, testInfo) => {
      await page.setViewportSize(viewport);
      await page.addInitScript((mode) => window.localStorage.setItem("veri-kalitesi-theme", mode), colorMode);
      await page.goto("/rules");

      await expect(page.locator("html")).toHaveAttribute("data-theme", colorMode);
      await expect(page.getByRole("heading", { level: 1, name: "Kurallar" })).toBeVisible();
      await expect(page.getByRole("heading", { level: 2, name: "Kural Envanteri" })).toBeVisible();
      await expect(page.getByLabel("Durum: Kritik").first()).toBeVisible();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(1);
      await page.screenshot({ path: testInfo.outputPath(`rules--${colorMode}--${viewport.name}.png`), fullPage: true });
    });
  }
}

test("kural ikonları aynı dikey eksende kalır ve filtreler birlikte uygulanır", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/rules");
  const iconSlots = page.getByTestId("rule-icon-slot");
  await expect(iconSlots).toHaveCount(5);
  const centers = await iconSlots.evaluateAll((slots) => slots.map((slot) => {
    const bounds = slot.getBoundingClientRect();
    return bounds.left + bounds.width / 2;
  }));
  expect(Math.max(...centers) - Math.min(...centers)).toBeLessThanOrEqual(0.5);

  await page.getByLabel("Kural ara").fill("risk");
  await expect(page.getByText("Risk skoru geçerlilik aralığı")).toBeVisible();
  await expect(page.getByText("Müşteri kimliği zorunluluğu")).not.toBeVisible();
  await page.getByLabel("Kural ara").fill("");
  await page.getByLabel("Kritiklik").click();
  await page.getByRole("option", { name: "Düşük" }).click();
  await expect(page.getByText("Şube kodu referans bütünlüğü")).toBeVisible();
  await expect(page.getByText("IBAN tekillik kontrolü")).not.toBeVisible();
});

test("yetkisiz kurallar yüzeyi veri ifşa etmez ve klavyeyle erişilir", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/rules?state=unauthorized");
  await expect(page.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();
  await expect(page.getByLabel("Kural ara")).not.toBeVisible();
  for (let attempt = 0; attempt < 8; attempt += 1) {
    await page.keyboard.press("Tab");
    const hasVisibleFocus = await page.evaluate(() => document.activeElement?.matches(":focus-visible") ?? false);
    if (hasVisibleFocus) break;
  }
  await expect(page.getByText("Müşteri kimliği zorunluluğu")).not.toBeVisible();
  const outline = await page.evaluate(() => getComputedStyle(document.activeElement as Element).outlineStyle);
  expect(outline).not.toBe("none");
  await page.screenshot({ path: testInfo.outputPath("rules--unauthorized--1366x768.png"), fullPage: true });
});

function ruleFixture() {
  return {
    api_version: "v1",
    data_origin: "synthetic-development",
    correlation_id: "e2e-rules",
    items: [
      { quality_rule_id: "rule-customer-id-required", code: "DQ_CUSTOMER_ID_REQUIRED", name: "Müşteri kimliği zorunluluğu", dataset_id: "dataset-customer", primary_dimension: "COMPLETENESS", status: "ACTIVE", rule_version_id: "version-3", version_no: 3, rule_type: "REQUIRED", criticality: "CRITICAL", created_at: "2026-07-19T08:30:00Z" },
      { quality_rule_id: "rule-account-iban-unique", code: "DQ_ACCOUNT_IBAN_UNIQUE", name: "IBAN tekillik kontrolü", dataset_id: "dataset-account", primary_dimension: "UNIQUENESS", status: "ACTIVE", rule_version_id: "version-2", version_no: 2, rule_type: "UNIQUE", criticality: "HIGH", created_at: "2026-07-18T10:15:00Z" },
      { quality_rule_id: "rule-risk-score-range", code: "DQ_RISK_SCORE_RANGE", name: "Risk skoru geçerlilik aralığı", dataset_id: "dataset-risk", primary_dimension: "VALIDITY", status: "REVIEW_REQUIRED", rule_version_id: "version-4", version_no: 4, rule_type: "RANGE", criticality: "CRITICAL", created_at: "2026-07-21T13:45:00Z" },
      { quality_rule_id: "rule-transaction-freshness", code: "DQ_TRANSACTION_FRESHNESS", name: "İşlem verisi güncelliği", dataset_id: "dataset-transaction", primary_dimension: "TIMELINESS", status: "DRAFT", rule_version_id: "version-1", version_no: 1, rule_type: "FRESHNESS", criticality: "MEDIUM", created_at: "2026-07-22T07:05:00Z" },
      { quality_rule_id: "rule-branch-code-reference", code: "DQ_BRANCH_CODE_REFERENCE", name: "Şube kodu referans bütünlüğü", dataset_id: "dataset-account", primary_dimension: "INTEGRITY", status: "PASSIVE", rule_version_id: "version-branch-2", version_no: 2, rule_type: "REFERENTIAL_INTEGRITY", criticality: "LOW", created_at: "2026-07-17T09:00:00Z" },
    ],
  };
}
