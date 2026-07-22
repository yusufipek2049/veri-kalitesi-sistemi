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
  await page.route("**/api/v1/dashboard/summary", async (route) => {
    await route.fulfill({
      body: JSON.stringify(dashboardApiFixture()),
      contentType: "application/json",
      headers: { "X-Correlation-ID": "e2e-dashboard-correlation" },
      status: 200,
    });
  });
});

for (const viewport of viewports) {
  for (const colorMode of ["light", "dark"] as const) {
    test(`dashboard ${viewport.name} ${colorMode} görünümünde taşma üretmez`, async ({ page }, testInfo) => {
      await page.setViewportSize(viewport);
      await page.addInitScript((mode) => window.localStorage.setItem("veri-kalitesi-theme", mode), colorMode);
      await page.goto("/");
      await expect(page.locator("html")).toHaveAttribute("data-theme", colorMode);
      await expect(page.getByRole("heading", { level: 1, name: "Genel Bakış" })).toBeVisible();
      await expect(page.getByText("SENTETİK VERİ")).toBeVisible();
      await expect(page.getByText(/Yerel dashboard API'si sentetik geliştirme skorlarıyla bağlıdır/)).toBeVisible();
      await expect(page.getByRole("img", { name: /Resmî nihai skor trendi/ })).toBeVisible();

      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(1);

      await page.screenshot({
        path: testInfo.outputPath(`dashboard--normal--${colorMode}--${viewport.name}.png`),
        fullPage: true,
      });
    });
  }
}

test("navigasyon grupları ve ikon merkezleri referans hiyerarşisini korur", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "ANALİZ" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "OPERASYON" })).toBeVisible();
  const iconSlots = page.getByTestId("navigation-icon-slot");
  await expect(iconSlots).toHaveCount(7);
  const centers = await iconSlots.evaluateAll((slots) => slots.map((slot) => {
    const bounds = slot.getBoundingClientRect();
    return bounds.left + bounds.width / 2;
  }));
  expect(Math.max(...centers) - Math.min(...centers)).toBeLessThanOrEqual(0.5);
});

test("tema seçimi kalıcıdır ve erişilebilir adı değişir", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Koyu temaya geç" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.getByRole("button", { name: "Açık temaya geç" })).toBeVisible();

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("grafik ve erişilebilir tablo aynı gözlemleri kullanır", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Tablo" }).click();

  const table = page.getByRole("table", { name: "Veri kalitesi trend tablosu" });
  await expect(table).toBeVisible();
  await expect(table.getByRole("row")).toHaveCount(31);
  await expect(table.getByRole("cell", { name: "Resmî", exact: true })).toHaveCount(7);
});

test("21C operasyonel göstergeleri ve sentetik karşılaştırmalar ayrı sunulur", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("Doğrulama Gerekli")).toBeVisible();
  await expect(page.getByText("Kritik kural sonuç kaynağı henüz bağlı değil")).toBeVisible();
  await expect(page.getByLabel("Durum: Teknik Hata Yok")).toBeVisible();
  await expect(page.getByRole("progressbar")).toHaveCount(5);
  const matrix = page.getByRole("table", { name: "Sentetik kalite boyutu matrisi" });
  await expect(matrix).toBeVisible();
  await expect(matrix.getByRole("row")).toHaveCount(6);
  await expect(matrix.getByLabel("Operasyon, Güncellik: Hesaplanmadı, Hesaplanmadı")).toHaveText("—");
  const matrixOverflow = await matrix.evaluate((element) => element.scrollWidth - element.clientWidth);
  expect(matrixOverflow).toBeLessThanOrEqual(1);
});

function dashboardApiFixture() {
  const start = new Date("2026-06-23T00:00:00Z");
  const scores = new Map<number, number>([
    [0, 72.1],
    [4, 76.8],
    [8, 78.2],
    [16, 82.4],
    [20, 84.6],
    [24, 86.2],
    [28, 87.4],
  ]);
  const periods = Array.from({ length: 30 }, (_, index) => {
    const periodStart = new Date(start);
    periodStart.setUTCDate(start.getUTCDate() + index);
    const periodEnd = new Date(periodStart);
    periodEnd.setUTCDate(periodStart.getUTCDate() + 1);
    const score = scores.get(index);
    return {
      period_start: periodStart.toISOString(),
      period_end: periodEnd.toISOString(),
      observations: score === undefined ? [] : [{
        quality_score_id: `e2e-score-${index}`,
        scope_type: "ENTERPRISE",
        scope_id: null,
        score_value: score.toFixed(2),
        score_status: "CALCULATED",
        level: "ACCEPTABLE",
        calculated_at: periodStart.toISOString(),
      }],
    };
  });
  return {
    api_version: "v1",
    data_origin: "synthetic-development",
    correlation_id: "e2e-dashboard-correlation",
    as_of: "2026-07-22T12:00:00Z",
    has_data: true,
    periods,
    operational_indicators: {
      measurement_qualification: {
        status: "VALIDATION_REQUIRED",
        evaluated_scope_count: 1,
        reason_codes: ["QUALIFICATION_POLICY_UNAVAILABLE"],
        policy_version: null,
      },
      critical_controls: {
        status: "NOT_AVAILABLE",
        reason_code: "CRITICAL_RULE_RESULT_NOT_AVAILABLE",
        passed_count: null,
        failed_count: null,
        not_evaluated_count: null,
      },
      technical_errors: {
        observation_count: 0,
        execution_count: 0,
        affected_source_count: 0,
        last_occurred_at: null,
      },
    },
  };
}

test("klavye odağı görünür ve yetkisiz yüzey veri ifşa etmez", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/?state=unauthorized");
  await expect(page.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();

  for (let attempt = 0; attempt < 8; attempt += 1) {
    await page.keyboard.press("Tab");
    const hasVisibleFocus = await page.evaluate(() => document.activeElement?.matches(":focus-visible") ?? false);
    if (hasVisibleFocus) break;
  }

  const focusedElement = await page.evaluate(() => ({
    name: document.activeElement?.getAttribute("aria-label") ?? document.activeElement?.textContent,
    outline: getComputedStyle(document.activeElement as Element).outlineStyle,
  }));
  expect(focusedElement.name?.trim()).toBeTruthy();
  expect(focusedElement.outline).not.toBe("none");
  await expect(page.getByText("Nihai Kalite Skoru")).not.toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("dashboard--unauthorized--1366x768.png"),
    fullPage: true,
  });
});
