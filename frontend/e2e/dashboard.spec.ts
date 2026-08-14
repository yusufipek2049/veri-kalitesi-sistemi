import { expect, test } from "@playwright/test";

test("trend noktası zenginleştirilmiş tooltip içeriğini gösterir", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("development-user-id", "dev-data-viewer");
  });
  await page.route("**/api/v1/development/users", async (route) => {
    await route.fulfill({
      body: JSON.stringify({
        items: [{ user_id: "dev-data-viewer", display_name: "Veri Görüntüleyici", roles: "DATA_VIEWER" }],
      }),
      contentType: "application/json",
      status: 200,
    });
  });
  await page.route("**/api/v1/dashboard/overview", async (route) => {
    await route.fulfill({
      body: JSON.stringify(dashboardFixture()),
      contentType: "application/json",
      status: 200,
    });
  });

  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { level: 2, name: "Kalite Trendi" })).toBeVisible();

  const chart = page.getByRole("img", { name: /Kalite trend grafiği/ });
  await expect(chart).toBeVisible();
  const bounds = await chart.boundingBox();
  if (!bounds) throw new Error("Trend grafiğinin sınırları belirlenemedi.");

  // Üç kategorinin ortasındaki noktanın axis-trigger alanına gel.
  await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);

  const tooltip = page.getByTestId("trend-tooltip");
  await expect(tooltip).toBeVisible();
  await expect(tooltip).toContainText("08.08 – 14.08");
  await expect(tooltip).toContainText("Skor: 84.2");
  await expect(tooltip).toContainText("GOOD");
  await expect(tooltip).toContainText("Durum: Hesaplandı");
  await expect(tooltip).toContainText("Değişim: +2.4");
  await expect(tooltip).toContainText("Karşılaştırma: Karşılaştırılamaz");
  await expect(tooltip).toContainText("POLICY_VERSION_CHANGED, NON_OFFICIAL_RESULT");
});

function dashboardFixture() {
  return {
    api_version: "v1",
    data_origin: "e2e",
    correlation_id: "e2e-dashboard",
    trend: {
      as_of: "2026-08-21T12:00:00+03:00",
      has_data: true,
      periods: [
        period("2026-08-01T00:00:00+03:00", "2026-08-07T23:59:59+03:00", 81.8, 1.1, "COMPARABLE", []),
        period(
          "2026-08-08T00:00:00+03:00",
          "2026-08-14T23:59:59+03:00",
          84.2,
          2.4,
          "NOT_COMPARABLE",
          ["POLICY_VERSION_CHANGED", "NON_OFFICIAL_RESULT"],
        ),
        period("2026-08-15T00:00:00+03:00", "2026-08-21T23:59:59+03:00", 85.3, 1.1, "COMPARABLE", []),
      ],
    },
    operational_indicators: {
      measurement_qualification: {
        status: "VALIDATION_REQUIRED",
        evaluated_scope_count: 1,
        reason_codes: [],
      },
      technical_errors: {
        observation_count: 0,
        execution_count: 0,
        affected_source_count: 0,
        last_occurred_at: null,
      },
    },
    role_view: "QUALITY_MANAGER",
  };
}

function period(
  periodStart: string,
  periodEnd: string,
  scoreValue: number,
  change: number,
  comparisonStatus: string,
  comparisonReasonCodes: string[],
) {
  return {
    period_start: periodStart,
    period_end: periodEnd,
    observations: [{
      quality_score_id: `score-${periodStart}`,
      scope_type: "ENTERPRISE",
      scope_id: null,
      score_value: scoreValue,
      score_status: "CALCULATED",
      level: "GOOD",
      calculated_at: periodEnd,
      comparison_status: comparisonStatus,
      comparison_reason_codes: comparisonReasonCodes,
      change,
      version_boundary: comparisonStatus === "NOT_COMPARABLE",
      policy_version: "v2",
    }],
  };
}
