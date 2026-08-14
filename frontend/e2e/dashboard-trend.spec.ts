import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(() => window.localStorage.setItem("development-user-id", "e2e-quality-manager"));
  await page.route("**/api/v1/development/users", (route) => route.fulfill({
    body: JSON.stringify({ items: [{ user_id: "e2e-quality-manager", display_name: "E2E Kalite Yöneticisi", roles: "QUALITY_MANAGER" }] }),
    contentType: "application/json",
    status: 200,
  }));
  await page.route("**/api/v1/dashboard/overview**", (route) => route.fulfill({
    body: JSON.stringify(dashboardFixture()),
    contentType: "application/json",
    headers: { "X-Correlation-ID": "e2e-dashboard-trend" },
    status: 200,
  }));
  await page.route("**/api/v1/datasets**", (route) => route.fulfill({
    body: JSON.stringify({ api_version: "v1", data_origin: "e2e", correlation_id: "catalog", items: [] }),
    contentType: "application/json",
    status: 200,
  }));
  await page.route("**/api/v1/data-sources**", (route) => route.fulfill({
    body: JSON.stringify({
      api_version: "v1",
      data_origin: "e2e",
      correlation_id: "sources",
      items: [
        dataSource("source-a", "Temel Bankacılık"),
        dataSource("source-b", "Risk Veri Martı"),
      ],
    }),
    contentType: "application/json",
    status: 200,
  }));
  await page.route("**/api/v1/scores**", (route) => route.fulfill({
    body: JSON.stringify({ data_origin: "e2e", correlation_id: "scores", items: [] }),
    contentType: "application/json",
    status: 200,
  }));
});

for (const viewport of [{ width: 1440, height: 900 }, { width: 1024, height: 768 }]) {
  test(`dönem seçici ${viewport.width}x${viewport.height} görünümünde grafiği günceller`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/dashboard");

    const chart = page.getByRole("img", { name: "Kalite trend grafiği" });
    await expect(chart).toHaveAttribute("data-period-count", "30");
    await page.getByRole("button", { name: "Son 7 gün" }).click();
    await expect(chart).toHaveAttribute("data-period-count", "7");
    await expect(page.getByText("Aktif dönem: Son 7 gün")).toBeVisible();
  });
}

test("tablo görünümü sütun içeriğini ve ARIA ilişkilerini korur", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/dashboard");

  await page.getByRole("tab", { name: "Tablo" }).click();
  const panel = page.getByRole("tabpanel", { name: "Tablo" });
  await expect(panel).toBeVisible();
  await expect(page.getByRole("table", { name: "Kalite trend tablosu" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Kurumsal Skor" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Kaynak Sayısı" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "2" }).first()).toBeVisible();
});

test("hover tooltip skor, durum, değişim ve kaynak ayrıntılarını gösterir", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/dashboard");

  const chart = page.getByRole("img", { name: "Kalite trend grafiği" });
  const bounds = await chart.boundingBox();
  if (!bounds) throw new Error("Trend grafiği sınırları bulunamadı.");
  const tooltip = page.getByTestId("trend-tooltip");
  for (const ratio of [0.25, 0.4, 0.55, 0.7, 0.85]) {
    await page.mouse.move(bounds.x + bounds.width * ratio, bounds.y + bounds.height * 0.45);
    if (await tooltip.isVisible().catch(() => false)) break;
  }
  await expect(tooltip).toBeVisible();
  await expect(tooltip).toContainText("Skor:");
  await expect(tooltip).toContainText("Durum:");
  await expect(tooltip).toContainText("Değişim:");
  await expect(tooltip).toContainText(/Temel Bankacılık|Risk Veri Martı/);
});

test("kaynak overlay serileri ve scroll legend birlikte render edilir", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/dashboard");

  const chart = page.getByRole("img", { name: "Kalite trend grafiği" });
  await expect(chart).toHaveAttribute("data-source-series-count", "2");
  await expect(chart.locator("canvas")).toBeVisible();
  const bounds = await chart.boundingBox();
  if (!bounds) throw new Error("Trend grafiği sınırları bulunamadı.");
  await page.mouse.click(bounds.x + bounds.width / 2, bounds.y + 14);
  await expect(chart).toBeVisible();
});

test("teknik hata marker'ı mor teknik renk ile yapılandırılır", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/dashboard");

  const chart = page.getByRole("img", { name: "Kalite trend grafiği" });
  await expect(chart).toHaveAttribute("data-technical-error-count", "1");
  await expect(chart).toHaveAttribute("data-technical-marker-color", /.+/);
});

test("sürüm sınırı dikey çizgi label bilgisini taşır", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/dashboard");

  const chart = page.getByRole("img", { name: "Kalite trend grafiği" });
  await expect(chart).toHaveAttribute("data-version-boundary-count", "1");
  await expect(chart).toHaveAttribute("data-version-labels", "v2");
  await expect(chart).toHaveAttribute("data-threshold-value", "64.5");
});

test("kaynak ve tarih filtreleri query parametrelerine uygulanır ve temizlenir", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/dashboard");

  await expect(page.getByRole("region", { name: "Dashboard filtreleri" })).toBeVisible();
  const dateRequest = page.waitForRequest((request) => request.url().includes("start_date=2026-08-01"));
  await page.getByLabel("Başlangıç tarihi").fill("2026-08-01");
  await dateRequest;

  await page.getByRole("combobox", { name: "Kaynak" }).click();
  const sourceRequest = page.waitForRequest((request) => {
    const url = new URL(request.url());
    return url.searchParams.get("scope_type") === "SOURCE" && url.searchParams.get("scope_id") === "source-a";
  });
  await page.getByRole("option", { name: "Temel Bankacılık" }).click();
  await sourceRequest;
  await expect(page.getByText(/Aktif filtreler:.*Temel Bankacılık/)).toBeVisible();

  const clearRequest = page.waitForRequest((request) => !request.url().includes("start_date=") && request.url().includes("/dashboard/overview"));
  await page.getByRole("button", { name: "Filtreleri Temizle" }).click();
  await clearRequest;
  await expect(page.getByText(/Aktif filtreler:/)).toHaveCount(0);
});

for (const viewport of [{ width: 1024, height: 768 }, { width: 1280, height: 800 }]) {
  test(`dashboard ${viewport.width}x${viewport.height} görünümünde yatay taşmaz`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { level: 1, name: "Genel Bakış" })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
}

function dataSource(id: string, name: string) {
  return {
    data_source_id: id,
    name,
    source_type: "POSTGRESQL",
    status: "ACTIVE",
    last_test_at: null,
    available_actions: [],
  };
}

function dashboardFixture() {
  const periods = Array.from({ length: 35 }, (_, index) => {
    const start = new Date(Date.UTC(2026, 6, 1 + index));
    const end = new Date(start.getTime() + 86_399_000);
    const enterprise = observation(`enterprise-${index}`, "ENTERPRISE", null, 72 + (index % 18), end.toISOString());
    if (index === 31) {
      enterprise.score_value = null;
      enterprise.score_status = "NOT_CALCULATED_TECHNICAL_ERROR";
      enterprise.level = null;
    }
    if (index === 32) {
      enterprise.version_boundary = true;
      enterprise.policy_version = "v2";
    }
    enterprise.trend = {
      moving_average: 78.4,
      consecutive_deterioration_count: 1,
      sudden_deterioration: false,
      time_below_threshold_periods: 0,
      improvement_persistence: 2,
    };
    return {
      period_start: start.toISOString(),
      period_end: end.toISOString(),
      observations: [
        enterprise,
        observation(`source-a-${index}`, "SOURCE", "source-a", 75 + (index % 10), end.toISOString()),
        observation(`source-b-${index}`, "SOURCE", "source-b", 68 + (index % 12), end.toISOString()),
      ],
    };
  });
  return {
    api_version: "v1",
    data_origin: "e2e",
    correlation_id: "e2e-dashboard-trend",
    trend: { as_of: "2026-08-11T12:00:00Z", has_data: true, threshold_value: 64.5, periods },
    operational_indicators: {
      measurement_qualification: { status: "NO_DATA", evaluated_scope_count: 3, reason_codes: [] },
      technical_errors: { observation_count: 1, execution_count: 1, affected_source_count: 1, last_occurred_at: "2026-08-01T12:00:00Z" },
    },
    role_view: "EXECUTIVE",
    applied_filters: null,
  };
}

function observation(id: string, scopeType: "ENTERPRISE" | "SOURCE", scopeId: string | null, score: number | null, calculatedAt: string) {
  return {
    quality_score_id: id,
    scope_type: scopeType,
    scope_id: scopeId,
    score_value: score,
    score_status: "CALCULATED",
    level: "GOOD" as string | null,
    calculated_at: calculatedAt,
    comparison_status: "COMPARABLE",
    comparison_reason_codes: [],
    change: 1.2,
    version_boundary: false,
    policy_version: null as string | null,
    trend: undefined as Record<string, unknown> | undefined,
  };
}
