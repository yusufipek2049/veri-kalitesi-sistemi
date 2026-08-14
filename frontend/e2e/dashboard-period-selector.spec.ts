import { expect, test } from "@playwright/test";

const viewports = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "laptop", width: 1024, height: 768 },
  { name: "mobile", width: 390, height: 844 },
];

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(() => window.localStorage.setItem("development-user-id", "e2e-quality-manager"));
  await page.route("**/api/v1/development/users", (route) => route.fulfill({
    body: JSON.stringify({ items: [{ user_id: "e2e-quality-manager", display_name: "E2E Kalite Yöneticisi", roles: "QUALITY_MANAGER" }] }),
    contentType: "application/json",
    status: 200,
  }));
  await page.route("**/api/v1/dashboard/overview", (route) => route.fulfill({
    body: JSON.stringify(dashboardFixture()),
    contentType: "application/json",
    status: 200,
  }));
  await page.route("**/api/v1/datasets**", (route) => route.fulfill({
    body: JSON.stringify({ api_version: "v1", data_origin: "e2e", correlation_id: "e2e-catalog", items: [] }),
    contentType: "application/json",
    status: 200,
  }));
  await page.route("**/api/v1/data-sources**", (route) => route.fulfill({
    body: JSON.stringify({ api_version: "v1", data_origin: "e2e", correlation_id: "e2e-sources", items: [] }),
    contentType: "application/json",
    status: 200,
  }));
  await page.route("**/api/v1/scores**", (route) => route.fulfill({
    body: JSON.stringify({ data_origin: "e2e", correlation_id: "e2e-scores", items: [] }),
    contentType: "application/json",
    status: 200,
  }));
});

for (const viewport of viewports) {
  test(`dönem seçici ${viewport.name} görünümünde erişilebilir`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/dashboard");

    const group = page.getByRole("group", { name: "Trend dönemi" });
    const sevenDays = page.getByRole("button", { name: "Son 7 gün" });
    const fourteenDays = page.getByRole("button", { name: "Son 14 gün" });
    const thirtyDays = page.getByRole("button", { name: "Son 30 gün" });

    await expect(group).toBeVisible();
    await expect(sevenDays).toHaveAttribute("aria-pressed", "false");
    await expect(fourteenDays).toHaveAttribute("aria-pressed", "false");
    await expect(thirtyDays).toHaveAttribute("aria-pressed", "true");

    await sevenDays.focus();
    await page.keyboard.press("Space");
    await expect(sevenDays).toHaveAttribute("aria-pressed", "true");
    await expect(thirtyDays).toHaveAttribute("aria-pressed", "false");
    await expect(page.getByText("Aktif dönem: Son 7 gün")).toBeVisible();
    await expect(page.getByRole("img", { name: "Kalite trend grafiği" })).toHaveAttribute("data-period-count", "7");

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
}

function dashboardFixture() {
  const periods = Array.from({ length: 35 }, (_, index) => {
    const start = new Date(Date.UTC(2026, 6, 1 + index));
    const end = new Date(start.getTime() + 86_399_000);
    return {
      period_start: start.toISOString(),
      period_end: end.toISOString(),
      observations: [{
        quality_score_id: `enterprise-${index}`,
        scope_type: "ENTERPRISE",
        scope_id: null,
        score_value: 70 + (index % 20),
        score_status: "CALCULATED",
        level: "GOOD",
        calculated_at: end.toISOString(),
        comparison_status: "COMPARABLE",
        comparison_reason_codes: [],
        change: 1,
      }],
    };
  });

  return {
    api_version: "v1",
    data_origin: "e2e",
    correlation_id: "e2e-dashboard-period-selector",
    trend: { as_of: "2026-08-04T23:59:59Z", has_data: true, periods },
    operational_indicators: {
      measurement_qualification: { status: "NO_DATA", evaluated_scope_count: 1, reason_codes: [] },
      technical_errors: { observation_count: 0, execution_count: 0, affected_source_count: 0, last_occurred_at: null },
    },
    role_view: "ADMIN",
  };
}
