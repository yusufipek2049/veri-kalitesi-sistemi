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
  await page.route("**/api/v1/audit/events**", async (route) => {
    await route.fulfill({
      body: JSON.stringify(auditFixture()),
      contentType: "application/json",
      headers: { "X-Correlation-ID": "e2e-audit" },
      status: 200,
    });
  });
});

for (const viewport of viewports) {
  for (const colorMode of ["light", "dark"] as const) {
    test(`denetim ${viewport.name} ${colorMode} görünümünde taşma üretmez`, async ({
      page,
    }, testInfo) => {
      await page.setViewportSize(viewport);
      await page.addInitScript(
        (mode) => window.localStorage.setItem("veri-kalitesi-theme", mode),
        colorMode,
      );
      await page.goto("/audit");

      await expect(page.locator("html")).toHaveAttribute("data-theme", colorMode);
      await expect(
        page.getByRole("heading", { level: 1, name: "Denetim" }),
      ).toBeVisible();
      await expect(page.getByText("Bütünlük doğrulandı")).toBeVisible();
      await expect(page.getByText("Başarısız")).toBeVisible();
      await expect(page.getByText("Reddedildi")).toBeVisible();
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(1);
      await page.screenshot({
        path: testInfo.outputPath(`audit--${colorMode}--${viewport.name}.png`),
        fullPage: true,
      });
    });
  }
}

test("audit ikonları aynı dikey eksende kalır ve filtreler temizlenir", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/audit");
  const iconSlots = page.getByTestId("audit-icon-slot");
  await expect(iconSlots).toHaveCount(6);
  const centers = await iconSlots.evaluateAll((slots) =>
    slots.map((slot) => {
      const bounds = slot.getBoundingClientRect();
      return bounds.left + bounds.width / 2;
    }),
  );
  expect(Math.max(...centers) - Math.min(...centers)).toBeLessThanOrEqual(0.5);

  await page.getByLabel("Aktör").fill("rule-checker");
  await expect(page.getByText("Kural aktivasyonu")).toBeVisible();
  await expect(page.getByText("Bağlantı testi")).not.toBeVisible();
  await page.getByRole("button", { name: "Filtreleri temizle" }).click();
  await page.getByRole("combobox", { name: "Sonuç" }).click();
  await page.getByRole("option", { name: "Reddedildi" }).click();
  await expect(page.getByText("Skor politikası aktivasyonu")).toBeVisible();
  await expect(page.getByText("Kural aktivasyonu")).not.toBeVisible();
});

test("yetkisiz denetim yüzeyi veri ifşa etmez ve klavyeyle erişilir", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/audit?state=unauthorized");
  await expect(page.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();
  await expect(page.getByLabel("Aktör")).not.toBeVisible();
  for (let attempt = 0; attempt < 8; attempt += 1) {
    await page.keyboard.press("Tab");
    const hasVisibleFocus = await page.evaluate(
      () => document.activeElement?.matches(":focus-visible") ?? false,
    );
    if (hasVisibleFocus) break;
  }
  await expect(page.getByText("Kural aktivasyonu")).not.toBeVisible();
  const outline = await page.evaluate(
    () => getComputedStyle(document.activeElement as Element).outlineStyle,
  );
  expect(outline).not.toBe("none");
  await page.screenshot({
    path: testInfo.outputPath("audit--unauthorized--1366x768.png"),
    fullPage: true,
  });
});

function auditFixture() {
  return {
    api_version: "v1",
    data_origin: "synthetic-development",
    correlation_id: "e2e-audit",
    period_start: "2026-07-16T12:00:00Z",
    period_end: "2026-07-23T12:00:00Z",
    integrity_valid: true,
    integrity_checked_count: 6,
    next_after_sequence_no: null,
    through_sequence_no: 6,
    page_size: 50,
    policy_version: "DEVELOPMENT_AUDIT_ACCESS_V1",
    items: [
      event(1, "LDAP_AUTHENTICATION", "UserSession", "SUCCESS", "AUTHENTICATED", "iam-user"),
      event(2, "DATA_SOURCE_CONNECTION_TEST", "DataSource", "SUCCESS", "TEST_SUCCEEDED", "data-steward"),
      event(3, "RULE_ACTIVATION", "QualityRule", "SUCCESS", "APPROVED", "rule-checker"),
      event(4, "SCORING_CONFIGURATION_ACTIVATION", "ScoringConfiguration", "DENIED", "MAKER_CHECKER_REQUIRED", "score-checker"),
      event(5, "REPORT_PREVIEW_VIEWED", "ReportPreview", "SUCCESS", "QUERY_COMPLETED", "report-viewer"),
      event(6, "IDENTITY_SESSION", "UserSession", "FAILURE", "ABSOLUTE_TIMEOUT", "session-user"),
    ],
  };
}

function event(
  sequence: number,
  action: string,
  objectType: string,
  result: string,
  reasonCode: string,
  actorId: string,
) {
  return {
    sequence_no: sequence,
    event_id: `audit-${sequence}`,
    occurred_at: `2026-07-${24 - sequence}T11:00:00Z`,
    actor_id: actorId,
    actor_type: "USER",
    correlation_id: `audit-correlation-${sequence}`,
    action,
    object_type: objectType,
    object_id: `object-${sequence}`,
    result,
    reason_code: reasonCode,
    redacted_field_count: 0,
  };
}
