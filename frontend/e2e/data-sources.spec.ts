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
  await page.route("**/api/v1/data-sources", async (route) => {
    await route.fulfill({
      body: JSON.stringify(dataSourceFixture()),
      contentType: "application/json",
      headers: { "X-Correlation-ID": "e2e-data-sources" },
      status: 200,
    });
  });
});

for (const viewport of viewports) {
  for (const colorMode of ["light", "dark"] as const) {
    test(`veri kaynakları ${viewport.name} ${colorMode} görünümünde taşma üretmez`, async ({ page }, testInfo) => {
      await page.setViewportSize(viewport);
      await page.addInitScript((mode) => window.localStorage.setItem("veri-kalitesi-theme", mode), colorMode);
      await page.goto("/data-sources");

      await expect(page.locator("html")).toHaveAttribute("data-theme", colorMode);
      await expect(page.getByRole("heading", { level: 1, name: "Veri Kaynakları" })).toBeVisible();
      await expect(page.getByRole("heading", { level: 2, name: "Kaynak Envanteri" })).toBeVisible();
      await expect(page.getByLabel("Durum: Aktif")).toBeVisible();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(1);
      await page.screenshot({ path: testInfo.outputPath(`data-sources--${colorMode}--${viewport.name}.png`), fullPage: true });
    });
  }
}

test("kaynak ikonları aynı dikey eksende kalır ve filtre uygulanır", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/data-sources");
  const iconSlots = page.getByTestId("source-icon-slot");
  await expect(iconSlots).toHaveCount(4);
  const centers = await iconSlots.evaluateAll((slots) => slots.map((slot) => {
    const bounds = slot.getBoundingClientRect();
    return bounds.left + bounds.width / 2;
  }));
  expect(Math.max(...centers) - Math.min(...centers)).toBeLessThanOrEqual(0.5);

  await page.getByLabel("Kaynak ara").fill("risk");
  await expect(page.getByText("Risk Veri Martı")).toBeVisible();
  await expect(page.getByText("Temel Bankacılık")).not.toBeVisible();
});

test("yetkisiz veri kaynakları yüzeyi veri ifşa etmez ve klavyeyle erişilir", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/data-sources?state=unauthorized");
  await expect(page.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();
  for (let attempt = 0; attempt < 8; attempt += 1) {
    await page.keyboard.press("Tab");
    const hasVisibleFocus = await page.evaluate(() => document.activeElement?.matches(":focus-visible") ?? false);
    if (hasVisibleFocus) break;
  }
  await expect(page.getByText("Temel Bankacılık")).not.toBeVisible();
  const outline = await page.evaluate(() => getComputedStyle(document.activeElement as Element).outlineStyle);
  expect(outline).not.toBe("none");
  await page.screenshot({ path: testInfo.outputPath("data-sources--unauthorized--1366x768.png"), fullPage: true });
});

function dataSourceFixture() {
  return {
    api_version: "v1",
    data_origin: "synthetic-development",
    correlation_id: "e2e-data-sources",
    items: [
      { data_source_id: "source-core-banking", name: "Temel Bankacılık", source_type: "POSTGRESQL", status: "ACTIVE", last_test_at: "2026-07-22T08:30:00Z" },
      { data_source_id: "source-customer-file", name: "Müşteri Dosyaları", source_type: "CSV", status: "TEST_SUCCEEDED", last_test_at: "2026-07-21T14:10:00Z" },
      { data_source_id: "source-risk-mart", name: "Risk Veri Martı", source_type: "MSSQL", status: "INACTIVE", last_test_at: "2026-07-18T11:45:00Z" },
      { data_source_id: "source-regulatory-api", name: "Düzenleyici Veri Servisi", source_type: "REST", status: "TEST_FAILED", last_test_at: "2026-07-22T07:05:00Z" },
    ],
  };
}
