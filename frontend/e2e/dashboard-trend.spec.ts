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
    body: JSON.stringify({
      api_version: "v1",
      data_origin: "e2e",
      correlation_id: "catalog",
      items: [
        dataset("dataset-a", "accounts", "source-a"),
        dataset("dataset-b", "transactions", "source-a"),
      ],
    }),
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
  await page.route("**/api/v1/scores/**", (route) => {
    // Skor detay istekleri (Detaylı Bilgi modalı)
    const scoreId = route.request().url().split("/scores/")[1]?.split("?")[0];
    return route.fulfill({
      body: JSON.stringify(scoreDetailFixture(scoreId ?? "score-unknown")),
      contentType: "application/json",
      status: 200,
    });
  });
  await page.route("**/api/v1/scores?*", (route) => route.fulfill({
    body: JSON.stringify({ data_origin: "e2e", correlation_id: "scores", items: datasetScoreFixture() }),
    contentType: "application/json",
    status: 200,
  }));
});

test("arama boşken genel ortalama gösterilir ve dataset serileri eklenmez", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/dashboard");

  await expect(page.getByText(/Genel ortalama sabit referans/)).toBeVisible();
  const chart = page.getByRole("img", { name: "Kalite trend grafiği" });
  await expect(chart).toHaveAttribute("data-has-average-series", "true");
  await expect(chart).toHaveAttribute("data-dataset-series-count", "0");
  await expect(chart.locator("canvas")).toBeVisible();
  await expect(page.getByRole("table", { name: "Kalite trend tablosu" })).toHaveCount(0);
});

for (const viewport of [{ width: 1440, height: 900 }, { width: 1024, height: 768 }]) {
  test(`arama girildiğinde dataset grafiği ${viewport.width}x${viewport.height} görünümünde render edilir`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/dashboard");

    await page.getByLabel("Dataset ara").fill("accounts");
    const chart = page.getByRole("img", { name: "Kalite trend grafiği" });
    await expect(chart).toHaveAttribute("data-dataset-series-count", "1");
    await expect(chart.locator("canvas")).toBeVisible();
  });
}

test("dönem seçici dataset geçmiş penceresini günceller", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/dashboard");

  await page.getByLabel("Dataset ara").fill("accounts");
  const chart = page.getByRole("img", { name: "Kalite trend grafiği" });
  await expect(chart).toHaveAttribute("data-day-count", "10");
  await page.getByRole("button", { name: "Son 7 gün" }).click();
  await expect(chart).toHaveAttribute("data-day-count", "7");
  await expect(page.getByText("Aktif dönem: Son 7 gün")).toBeVisible();
});

test("tablo görünümü dataset satırlarını ve Detaylı Bilgi butonunu gösterir", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/dashboard");

  await page.getByLabel("Dataset ara").fill("public");
  await page.getByRole("tab", { name: "Tablo" }).click();
  const panel = page.getByRole("tabpanel", { name: "Tablo" });
  await expect(panel).toBeVisible();
  await expect(page.getByRole("table", { name: "Kalite trend tablosu" })).toBeVisible();
  for (const header of ["Dataset", "Kaynak", "Son Skor", "Seviye", "Durum", "Zaman", "Detay"]) {
    await expect(page.getByRole("columnheader", { name: header })).toBeVisible();
  }
  await expect(page.getByRole("link", { name: "public.accounts" })).toBeVisible();
  await expect(page.getByRole("link", { name: "public.transactions" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Detaylı Bilgi/ }).first()).toBeVisible();
});

test("Detaylı Bilgi butonu skorlama parametrelerini modal üzerinde gösterir", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/dashboard");

  await page.getByLabel("Dataset ara").fill("accounts");
  await page.getByRole("tab", { name: "Tablo" }).click();
  await page.getByRole("button", { name: /Detaylı Bilgi/ }).first().click();

  await expect(page.getByText("Skorlama Detaylı Bilgi")).toBeVisible();
  await expect(page.getByText("Skorlama Parametreleri")).toBeVisible();
  await expect(page.getByText("logarithmic_improvement")).toBeVisible();
  await page.getByRole("button", { name: "Kapat" }).click();
  await expect(page.getByText("Skorlama Detaylı Bilgi")).toHaveCount(0);
});

test("hareketli ortalama seçeneği dashboard'da yer almaz", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/dashboard");

  await page.getByLabel("Dataset ara").fill("public");
  await expect(page.getByRole("img", { name: "Kalite trend grafiği" })).toBeVisible();
  await expect(page.getByText(/Hareketli Ortalama/i)).toHaveCount(0);
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

function dataset(datasetId: string, name: string, sourceId: string) {
  return {
    dataset_id: datasetId,
    data_source_id: sourceId,
    namespace: "public",
    name,
    dataset_type: "TABLE",
    status: "ACTIVE",
    criticality: "MEDIUM",
    estimated_row_count: null,
    field_count: 5,
    version: 1,
  };
}

function daysAgoIso(dayOffset: number): string {
  const date = new Date(Date.now() - dayOffset * 86_400_000);
  date.setUTCHours(8, 0, 0, 0);
  return date.toISOString();
}

// Logaritmik iyileşme eğrisi: value(t) = start + (asymptote - start) * ln(1+t) / ln(11)
function datasetScoreFixture() {
  const items: Array<Record<string, unknown>> = [];
  const configs = [
    { datasetId: "dataset-a", start: 58, asymptote: 94 },
    { datasetId: "dataset-b", start: 66, asymptote: 90 },
  ];
  for (const config of configs) {
    for (let dayOffset = 9; dayOffset >= 0; dayOffset--) {
      const t = 10 - dayOffset;
      const progress = Math.log(1 + t) / Math.log(11);
      const value = Math.round((config.start + (config.asymptote - config.start) * progress) * 10) / 10;
      items.push({
        quality_score_id: `score-${config.datasetId}-${t}`,
        execution_id: `exec-${config.datasetId}-${t}`,
        scope_type: "DATASET",
        scope_id: config.datasetId,
        scope_display_name: null,
        scope_parent_name: null,
        score_value: value,
        score_status: "CALCULATED",
        measurement_status: "Passed",
        level: value >= 90 ? "GOOD" : value >= 75 ? "ACCEPTABLE" : "RISKY",
        policy_version: "SEED_SCORING_V1",
        calculated_at: daysAgoIso(dayOffset),
        publication_id: "publication-e2e",
      });
    }
  }
  return items;
}

function scoreDetailFixture(qualityScoreId: string) {
  return {
    data_origin: "e2e",
    correlation_id: "score-detail",
    score: {
      quality_score_id: qualityScoreId,
      execution_id: "exec-detail",
      scope_type: "DATASET",
      scope_id: "dataset-a",
      scope_display_name: null,
      scope_parent_name: null,
      score_value: 91.5,
      score_status: "CALCULATED",
      measurement_status: "Passed",
      level: "GOOD",
      policy_version: "SEED_SCORING_V1",
      calculated_at: daysAgoIso(1),
      publication_id: "publication-e2e",
    },
    publication: {
      publication_id: "publication-e2e",
      execution_id: "exec-detail",
      period: "E2E_PERIOD",
      status: "PUBLISHED",
      policy_version: "SEED_SCORING_V1",
      published_at: daysAgoIso(1),
      superseded_at: null,
    },
    available_actions: [],
    has_contribution_graph: false,
    calculation_details: {
      curve: "logarithmic_improvement",
      parameters: { start: 58, asymptote: 94, window_days: 30 },
    },
    contribution_graph: null,
  };
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
        score_value: 72 + (index % 18),
        score_status: "CALCULATED",
        level: "GOOD",
        calculated_at: end.toISOString(),
        comparison_status: "COMPARABLE",
        comparison_reason_codes: [],
        change: 1.2,
        version_boundary: false,
        policy_version: null,
      }],
    };
  });
  return {
    api_version: "v1",
    data_origin: "e2e",
    correlation_id: "e2e-dashboard-trend",
    trend: { as_of: "2026-08-11T12:00:00Z", has_data: true, threshold_value: 64.5, periods },
    operational_indicators: {
      measurement_qualification: { status: "NO_DATA", evaluated_scope_count: 3, reason_codes: [] },
      technical_errors: { observation_count: 0, execution_count: 0, affected_source_count: 0, last_occurred_at: null },
    },
    role_view: "EXECUTIVE",
    applied_filters: null,
  };
}
