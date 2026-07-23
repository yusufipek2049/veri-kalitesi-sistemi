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
  await page.route("**/api/v1/executions", async (route) => {
    await route.fulfill({
      body: JSON.stringify(executionFixture()),
      contentType: "application/json",
      headers: { "X-Correlation-ID": "e2e-executions" },
      status: 200,
    });
  });
});

for (const viewport of viewports) {
  for (const colorMode of ["light", "dark"] as const) {
    test(`çalıştırmalar ${viewport.name} ${colorMode} görünümünde taşma üretmez`, async ({ page }, testInfo) => {
      await page.setViewportSize(viewport);
      await page.addInitScript((mode) => window.localStorage.setItem("veri-kalitesi-theme", mode), colorMode);
      await page.goto("/executions");

      await expect(page.locator("html")).toHaveAttribute("data-theme", colorMode);
      await expect(page.getByRole("heading", { level: 1, name: "Çalıştırmalar" })).toBeVisible();
      await expect(page.getByRole("heading", { level: 2, name: "Çalıştırma Geçmişi" })).toBeVisible();
      await expect(page.getByLabel("Durum: Teknik hata")).toBeVisible();
      await expect(page.getByLabel("Durum: Kısmi")).toBeVisible();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(1);
      await page.screenshot({ path: testInfo.outputPath(`executions--${colorMode}--${viewport.name}.png`), fullPage: true });
    });
  }
}

test("çalıştırma ikonları aynı dikey eksende kalır ve filtreler uygulanır", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/executions");
  const iconSlots = page.getByTestId("execution-icon-slot");
  await expect(iconSlots).toHaveCount(8);
  const centers = await iconSlots.evaluateAll((slots) => slots.map((slot) => {
    const bounds = slot.getBoundingClientRect();
    return bounds.left + bounds.width / 2;
  }));
  expect(Math.max(...centers) - Math.min(...centers)).toBeLessThanOrEqual(0.5);

  await page.getByLabel("Çalıştırma ara").fill("timeout");
  await expect(page.getByText("execution-timeout")).toBeVisible();
  await expect(page.getByText("execution-running")).not.toBeVisible();
  await page.getByLabel("Çalıştırma ara").fill("");
  await page.getByRole("combobox", { name: "Durum" }).click();
  await page.getByRole("option", { name: "Kısmi" }).click();
  await expect(page.getByText("execution-partial")).toBeVisible();
  await expect(page.getByText("execution-success")).not.toBeVisible();
});

test("yetkisiz çalıştırma yüzeyi veri ifşa etmez ve klavyeyle erişilir", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/executions?state=unauthorized");
  await expect(page.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();
  await expect(page.getByLabel("Çalıştırma ara")).not.toBeVisible();
  for (let attempt = 0; attempt < 8; attempt += 1) {
    await page.keyboard.press("Tab");
    const hasVisibleFocus = await page.evaluate(() => document.activeElement?.matches(":focus-visible") ?? false);
    if (hasVisibleFocus) break;
  }
  await expect(page.getByText("execution-running")).not.toBeVisible();
  const outline = await page.evaluate(() => getComputedStyle(document.activeElement as Element).outlineStyle);
  expect(outline).not.toBe("none");
  await page.screenshot({ path: testInfo.outputPath("executions--unauthorized--1366x768.png"), fullPage: true });
});

function executionFixture() {
  return {
    api_version: "v1",
    data_origin: "synthetic-development",
    correlation_id: "e2e-executions",
    limit: 100,
    items: [
      { execution_id: "execution-running", execution_type: "MANUAL", status: "RUNNING", workload_class: "HEAVY", rule_count: 2, source_count: 1, attempt_count: 1, error_class: null, created_at: "2026-07-23T08:40:00Z", started_at: "2026-07-23T08:41:00Z", finished_at: null },
      { execution_id: "execution-queued", execution_type: "SCHEDULED", status: "QUEUED", workload_class: "LIGHT", rule_count: 1, source_count: 1, attempt_count: 0, error_class: null, created_at: "2026-07-23T08:35:00Z", started_at: null, finished_at: null },
      { execution_id: "execution-success", execution_type: "SCHEDULED", status: "SUCCESS", workload_class: "LIGHT", rule_count: 1, source_count: 1, attempt_count: 1, error_class: null, created_at: "2026-07-23T07:15:00Z", started_at: "2026-07-23T07:16:00Z", finished_at: "2026-07-23T07:24:00Z" },
      { execution_id: "execution-partial", execution_type: "MANUAL", status: "PARTIAL", workload_class: "HEAVY", rule_count: 1, source_count: 1, attempt_count: 1, error_class: "QUERY_TIMEOUT", created_at: "2026-07-22T18:00:00Z", started_at: "2026-07-22T18:01:00Z", finished_at: "2026-07-22T18:31:00Z" },
      { execution_id: "execution-technical-error", execution_type: "MANUAL", status: "TECHNICAL_ERROR", workload_class: "LIGHT", rule_count: 1, source_count: 1, attempt_count: 3, error_class: "CONNECTION_UNAVAILABLE", created_at: "2026-07-22T14:20:00Z", started_at: "2026-07-22T14:21:00Z", finished_at: "2026-07-22T14:24:00Z" },
      { execution_id: "execution-timeout", execution_type: "MANUAL", status: "TIMEOUT", workload_class: "LIGHT", rule_count: 1, source_count: 1, attempt_count: 1, error_class: "TOTAL_TIMEOUT", created_at: "2026-07-21T11:00:00Z", started_at: "2026-07-21T11:01:00Z", finished_at: "2026-07-21T12:01:00Z" },
      { execution_id: "execution-cancel-requested", execution_type: "MANUAL", status: "CANCEL_REQUESTED", workload_class: "LIGHT", rule_count: 1, source_count: 1, attempt_count: 1, error_class: null, created_at: "2026-07-20T09:00:00Z", started_at: "2026-07-20T09:01:00Z", finished_at: null },
      { execution_id: "execution-cancelled", execution_type: "MANUAL", status: "CANCELLED", workload_class: "LIGHT", rule_count: 1, source_count: 1, attempt_count: 0, error_class: null, created_at: "2026-07-19T16:00:00Z", started_at: null, finished_at: "2026-07-19T16:02:00Z" },
    ],
  };
}
