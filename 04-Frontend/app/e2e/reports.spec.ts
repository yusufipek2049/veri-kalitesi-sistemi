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
  await page.route("**/api/v1/reports/summary", async (route) => {
    await route.fulfill({
      body: JSON.stringify(reportFixture()),
      contentType: "application/json",
      headers: { "X-Correlation-ID": "e2e-reports" },
      status: 200,
    });
  });
});

for (const viewport of viewports) {
  for (const colorMode of ["light", "dark"] as const) {
    test(`raporlar ${viewport.name} ${colorMode} görünümünde taşma üretmez`, async ({ page }, testInfo) => {
      await page.setViewportSize(viewport);
      await page.addInitScript((mode) => window.localStorage.setItem("veri-kalitesi-theme", mode), colorMode);
      await page.goto("/reports");

      await expect(page.locator("html")).toHaveAttribute("data-theme", colorMode);
      await expect(page.getByRole("heading", { level: 1, name: "Raporlar" })).toBeVisible();
      await expect(page.getByRole("heading", { level: 2, name: "Kaynak Skor Özeti" })).toBeVisible();
      await expect(page.getByLabel("Durum: Teknik hata")).toBeVisible();
      await expect(page.getByLabel("Durum: Veri yok")).toBeVisible();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(1);
      await page.screenshot({ path: testInfo.outputPath(`reports--${colorMode}--${viewport.name}.png`), fullPage: true });
    });
  }
}

test("rapor ikonları aynı dikey eksende kalır ve filtreler temizlenir", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/reports");
  const iconSlots = page.getByTestId("report-icon-slot");
  await expect(iconSlots).toHaveCount(4);
  const centers = await iconSlots.evaluateAll((slots) => slots.map((slot) => {
    const bounds = slot.getBoundingClientRect();
    return bounds.left + bounds.width / 2;
  }));
  expect(Math.max(...centers) - Math.min(...centers)).toBeLessThanOrEqual(0.5);

  await page.getByLabel("Kaynak ara").fill("risk");
  await expect(page.getByText("source-risk-mart")).toBeVisible();
  await expect(page.getByText("source-core-banking")).not.toBeVisible();
  await page.getByRole("button", { name: "Filtreleri temizle" }).click();
  await page.getByRole("combobox", { name: "Sonuç durumu" }).click();
  await page.getByRole("option", { name: "Teknik hata" }).click();
  await expect(page.getByText("source-regulatory-api")).toBeVisible();
  await expect(page.getByText("source-core-banking")).not.toBeVisible();
});

test("yetkisiz rapor yüzeyi veri ifşa etmez ve klavyeyle erişilir", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/reports?state=unauthorized");
  await expect(page.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();
  await expect(page.getByLabel("Kaynak ara")).not.toBeVisible();
  for (let attempt = 0; attempt < 8; attempt += 1) {
    await page.keyboard.press("Tab");
    const hasVisibleFocus = await page.evaluate(() => document.activeElement?.matches(":focus-visible") ?? false);
    if (hasVisibleFocus) break;
  }
  await expect(page.getByText("source-core-banking")).not.toBeVisible();
  const outline = await page.evaluate(() => getComputedStyle(document.activeElement as Element).outlineStyle);
  expect(outline).not.toBe("none");
  await page.screenshot({ path: testInfo.outputPath("reports--unauthorized--1366x768.png"), fullPage: true });
});

function reportFixture() {
  return {
    api_version: "v1",
    data_origin: "synthetic-development",
    correlation_id: "e2e-reports",
    report_type: "SUMMARY",
    created_at: "2026-07-23T12:00:00Z",
    period_start: "2026-06-23T12:00:00Z",
    period_end: "2026-07-23T12:00:00Z",
    source_count: 4,
    calculated_source_count: 2,
    average_score: "87.10",
    policy_version: "DEVELOPMENT_REPORT_POLICY_V1",
    masking_mode: "AGGREGATED_ONLY",
    rows: [
      { source_id: "source-core-banking", score_value: "91.80", score_status: "CALCULATED", level: "GOOD", calculated_at: "2026-07-23T11:00:00Z" },
      { source_id: "source-customer-file", score_value: "82.40", score_status: "PARTIAL", level: "ACCEPTABLE", calculated_at: "2026-07-23T10:00:00Z" },
      { source_id: "source-risk-mart", score_value: null, score_status: "NO_DATA", level: null, calculated_at: "2026-07-23T09:00:00Z" },
      { source_id: "source-regulatory-api", score_value: null, score_status: "NOT_CALCULATED_TECHNICAL_ERROR", level: null, calculated_at: "2026-07-23T08:00:00Z" },
    ],
  };
}
