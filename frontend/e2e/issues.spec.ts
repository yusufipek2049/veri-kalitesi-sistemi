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
  await page.route("**/api/v1/issues/*/assignment-options", async (route) => {
    await route.fulfill({
      body: JSON.stringify({
        api_version: "v1",
        data_origin: "synthetic-development",
        correlation_id: "e2e-assignment-options",
        items: [
          {
            user_id: "4ec96cb4-d150-45d2-9565-c1879d135f08",
            display_name: "Veri Sorumlusu A",
          },
          {
            user_id: "d6b099c7-0b6d-4ae5-8f58-6978050c434f",
            display_name: "Veri Sorumlusu B",
          },
        ],
      }),
      contentType: "application/json",
      status: 200,
    });
  });
  await page.route("**/api/v1/issues/*/assignment", async (route) => {
    const request = route.request();
    expect(request.method()).toBe("POST");
    expect(request.headers()["x-csrf-token"]).toBe("e2e-csrf-proof");
    expect(request.postDataJSON()).toEqual({
      version: 2,
      assignee_user_id: "4ec96cb4-d150-45d2-9565-c1879d135f08",
      priority: "MEDIUM",
    });
    const item = issueFixture().items[2];
    await route.fulfill({
      body: JSON.stringify({
        api_version: "v1",
        data_origin: "synthetic-development",
        correlation_id: "e2e-assignment",
        item: {
          ...item,
          status: "ASSIGNED",
          priority: "MEDIUM",
          version: 3,
          available_actions: ["REASSIGN"],
          updated_at: "2026-07-23T10:05:00Z",
        },
      }),
      contentType: "application/json",
      status: 200,
    });
  });
  await page.route("**/api/v1/issues/*/resolution", async (route) => {
    const request = route.request();
    expect(request.method()).toBe("POST");
    expect(request.headers()["x-csrf-token"]).toBe("e2e-csrf-proof");
    expect(request.postDataJSON()).toEqual(expect.objectContaining({
      version: 2,
      root_cause: "Kaynak eşlemesi hatalı",
      corrective_action: "Eşleme yapılandırması düzeltildi",
      evidence_reference_id: "550e8400-e29b-41d4-a716-446655440000",
    }));
    const item = issueFixture().items[2];
    await route.fulfill({
      body: JSON.stringify({
        api_version: "v1",
        data_origin: "synthetic-development",
        correlation_id: "e2e-resolution",
        item: {
          ...item,
          status: "RESOLVED",
          version: 3,
          available_actions: [],
          updated_at: "2026-07-23T12:30:00Z",
        },
      }),
      contentType: "application/json",
      status: 200,
    });
  });
  await page.route("**/api/v1/issues/*/investigation", async (route) => {
    const request = route.request();
    expect(request.method()).toBe("POST");
    expect(request.headers()["x-csrf-token"]).toBe("e2e-csrf-proof");
    expect(request.postDataJSON()).toEqual({ version: 1 });
    const item = issueFixture().items[1];
    await route.fulfill({
      body: JSON.stringify({
        api_version: "v1",
        data_origin: "synthetic-development",
        correlation_id: "e2e-investigation",
        item: {
          ...item,
          status: "INVESTIGATING",
          version: 2,
          available_actions: ["REASSIGN"],
          updated_at: "2026-07-23T10:00:00Z",
        },
      }),
      contentType: "application/json",
      status: 200,
    });
  });
  await page.route("**/api/v1/issues", async (route) => {
    await route.fulfill({
      body: JSON.stringify(issueFixture()),
      contentType: "application/json",
      headers: {
        "X-Correlation-ID": "e2e-issues",
        "X-CSRF-Token": "e2e-csrf-proof",
      },
      status: 200,
    });
  });
});

for (const viewport of viewports) {
  for (const colorMode of ["light", "dark"] as const) {
    test(`sorunlar ${viewport.name} ${colorMode} görünümünde taşma üretmez`, async ({ page }, testInfo) => {
      await page.setViewportSize(viewport);
      await page.addInitScript((mode) => window.localStorage.setItem("veri-kalitesi-theme", mode), colorMode);
      await page.goto("/issues");

      await expect(page.locator("html")).toHaveAttribute("data-theme", colorMode);
      await expect(page.getByRole("heading", { level: 1, name: "Sorunlar" })).toBeVisible();
      await expect(page.getByRole("heading", { level: 2, name: "Sorun Envanteri" })).toBeVisible();
      await expect(page.getByLabel("Durum: Kritik").first()).toBeVisible();
      await expect(page.getByLabel("Durum: Doğrulandı")).toBeVisible();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(1);
      await page.screenshot({ path: testInfo.outputPath(`issues--${colorMode}--${viewport.name}.png`), fullPage: true });
    });
  }
}

test("sorun ikonları aynı dikey eksende kalır ve filtreler temizlenir", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/issues");
  const iconSlots = page.getByTestId("issue-icon-slot");
  await expect(iconSlots).toHaveCount(8);
  const centers = await iconSlots.evaluateAll((slots) => slots.map((slot) => {
    const bounds = slot.getBoundingClientRect();
    return bounds.left + bounds.width / 2;
  }));
  expect(Math.max(...centers) - Math.min(...centers)).toBeLessThanOrEqual(0.5);

  await page.getByLabel("Sorun ara").fill("risk");
  await expect(page.getByText("DQI-2026-0017")).toBeVisible();
  await expect(page.getByText("DQI-2026-0018")).not.toBeVisible();
  await page.getByRole("button", { name: "Filtreleri temizle" }).click();
  await page.getByRole("combobox", { name: "Öncelik" }).click();
  await page.getByRole("option", { name: "Kritik" }).click();
  await expect(page.getByText("DQI-2026-0018")).toBeVisible();
  await expect(page.getByText("DQI-2026-0017")).not.toBeVisible();
});

test("atanan sorun incelemeye alınır ve eylem kapanır", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/issues");

  await page.getByRole("button", { name: "DQI-2026-0017 işlemleri" }).click();
  await page.getByRole("menuitem", { name: "İncelemeye al" }).click();

  await expect(page.getByText("DQI-2026-0017 incelemeye alındı.")).toBeVisible();
  await expect(page.getByLabel("Durum: İnceleniyor").first()).toBeVisible();
  await page.getByRole("button", { name: "DQI-2026-0017 işlemleri" }).click();
  await expect(page.getByRole("menuitem", { name: "İncelemeye al" })).not.toBeVisible();
  await expect(page.getByRole("menuitem", { name: "Yeniden ata" })).toBeVisible();
});

test("sorun yeniden atanır ve kaydedilmemiş değişiklik korunur", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/issues");

  await page.getByRole("button", { name: "DQI-2026-0016 işlemleri" }).click();
  await page.getByRole("menuitem", { name: "Yeniden ata" }).click();
  await page.getByRole("combobox", { name: "Yeni sorumlu" }).click();
  await page.getByRole("option", { name: "Veri Sorumlusu A" }).click();
  await page.screenshot({
    path: testInfo.outputPath("issues--assignment-dialog--1440x900.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Vazgeç" }).click();
  await expect(page.getByText("Değişiklikler kaydedilmedi")).toBeVisible();
  await page.getByRole("button", { name: "Forma dön" }).click();
  await page.getByRole("combobox", { name: "Öncelik" }).click();
  await page.getByRole("option", { name: "Orta" }).click();
  await page.getByRole("button", { name: "Kaydet" }).click();

  await expect(page.getByText("DQI-2026-0016 yeniden atandı.")).toBeVisible();
  await expect(page.getByLabel("Durum: Atandı").first()).toBeVisible();
});

test("sorun zorunlu kanıtla çözülür ve kaydedilmemiş çözüm korunur", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/issues");

  await page.getByRole("button", { name: "DQI-2026-0016 işlemleri" }).click();
  await page.getByRole("menuitem", { name: "Çözüm kaydet" }).click();
  await page.getByRole("textbox", { name: /Kök neden/ }).fill("Kaynak eşlemesi hatalı");
  await page.getByRole("textbox", { name: /Düzeltici faaliyet/ }).fill("Eşleme yapılandırması düzeltildi");
  await page.getByRole("textbox", { name: /Kanıt referansı/ }).fill("geçersiz-referans");
  await expect(page.getByText("Geçerli bir UUID girin.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Kaydet" })).toBeDisabled();
  await page.screenshot({
    path: testInfo.outputPath("issues--resolution-validation--1440x900.png"),
    fullPage: true,
  });

  await page.getByRole("button", { name: "Vazgeç" }).click();
  await expect(page.getByText("Değişiklikler kaydedilmedi")).toBeVisible();
  await page.getByRole("button", { name: "Forma dön" }).click();
  await page.getByRole("textbox", { name: /Kanıt referansı/ }).fill(
    "550e8400-e29b-41d4-a716-446655440000",
  );
  await page.getByLabel("Tamamlanma zamanı").fill("2026-07-23T09:30");
  await page.screenshot({
    path: testInfo.outputPath("issues--resolution-ready--1440x900.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Kaydet" }).click();

  await expect(page.getByText("DQI-2026-0016 çözüm kaydı oluşturuldu.")).toBeVisible();
  await expect(page.getByLabel("Durum: Çözüldü").first()).toBeVisible();
});

test("yetkisiz sorun yüzeyi veri ifşa etmez ve klavyeyle erişilir", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/issues?state=unauthorized");
  await expect(page.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();
  await expect(page.getByLabel("Sorun ara")).not.toBeVisible();
  for (let attempt = 0; attempt < 8; attempt += 1) {
    await page.keyboard.press("Tab");
    const hasVisibleFocus = await page.evaluate(() => document.activeElement?.matches(":focus-visible") ?? false);
    if (hasVisibleFocus) break;
  }
  await expect(page.getByText("DQI-2026-0018")).not.toBeVisible();
  const outline = await page.evaluate(() => getComputedStyle(document.activeElement as Element).outlineStyle);
  expect(outline).not.toBe("none");
  await page.screenshot({ path: testInfo.outputPath("issues--unauthorized--1366x768.png"), fullPage: true });
});

function issueFixture() {
  return {
    api_version: "v1",
    data_origin: "synthetic-development",
    correlation_id: "e2e-issues",
    limit: 100,
    items: [
      { issue_id: "issue-critical-customer", issue_no: "DQI-2026-0018", source_event_type: "QUALITY", trigger_type: "CRITICAL_RULE_FAILURE", scope_type: "DATASET", scope_id: "dataset-customer", status: "NEW", priority: "CRITICAL", occurrence_count: 1, version: 1, available_actions: [], created_at: "2026-07-23T08:10:00Z", updated_at: "2026-07-23T08:10:00Z", last_seen_at: "2026-07-23T08:10:00Z" },
      { issue_id: "issue-technical-risk", issue_no: "DQI-2026-0017", source_event_type: "TECHNICAL", trigger_type: "TECHNICAL_ERROR", scope_type: "SOURCE", scope_id: "source-risk-mart", status: "ASSIGNED", priority: "HIGH", occurrence_count: 3, version: 1, available_actions: ["START_INVESTIGATION", "REASSIGN"], created_at: "2026-07-22T15:00:00Z", updated_at: "2026-07-23T07:40:00Z", last_seen_at: "2026-07-23T07:40:00Z" },
      { issue_id: "issue-account-investigation", issue_no: "DQI-2026-0016", source_event_type: "QUALITY", trigger_type: "QUALITY_THRESHOLD", scope_type: "DATASET", scope_id: "dataset-account", status: "INVESTIGATING", priority: "HIGH", occurrence_count: 2, version: 2, available_actions: ["REASSIGN", "RESOLVE"], created_at: "2026-07-21T10:30:00Z", updated_at: "2026-07-22T16:20:00Z", last_seen_at: "2026-07-22T16:20:00Z" },
      { issue_id: "issue-transaction-waiting", issue_no: "DQI-2026-0015", source_event_type: "QUALITY", trigger_type: "QUALITY_THRESHOLD", scope_type: "DATASET", scope_id: "dataset-transaction", status: "WAITING_FOR_RESOLUTION", priority: "MEDIUM", occurrence_count: 4, version: 3, available_actions: ["RESOLVE"], created_at: "2026-07-19T09:00:00Z", updated_at: "2026-07-22T11:45:00Z", last_seen_at: "2026-07-22T11:45:00Z" },
      { issue_id: "issue-risk-resolved", issue_no: "DQI-2026-0014", source_event_type: "QUALITY", trigger_type: "CRITICAL_RULE_FAILURE", scope_type: "DATASET", scope_id: "dataset-risk", status: "RESOLVED", priority: "CRITICAL", occurrence_count: 1, version: 4, available_actions: [], created_at: "2026-07-18T13:15:00Z", updated_at: "2026-07-21T14:10:00Z", last_seen_at: "2026-07-18T13:15:00Z" },
      { issue_id: "issue-customer-verified", issue_no: "DQI-2026-0013", source_event_type: "QUALITY", trigger_type: "QUALITY_THRESHOLD", scope_type: "DATASET", scope_id: "dataset-customer", status: "VERIFIED", priority: "MEDIUM", occurrence_count: 1, version: 5, available_actions: [], created_at: "2026-07-17T12:00:00Z", updated_at: "2026-07-20T15:30:00Z", last_seen_at: "2026-07-17T12:00:00Z" },
      { issue_id: "issue-account-closed", issue_no: "DQI-2026-0012", source_event_type: "QUALITY", trigger_type: "QUALITY_THRESHOLD", scope_type: "DATASET", scope_id: "dataset-account", status: "CLOSED", priority: "LOW", occurrence_count: 1, version: 6, available_actions: [], created_at: "2026-07-15T08:00:00Z", updated_at: "2026-07-19T10:00:00Z", last_seen_at: "2026-07-15T08:00:00Z" },
      { issue_id: "issue-source-cancelled", issue_no: "DQI-2026-0011", source_event_type: "TECHNICAL", trigger_type: "TECHNICAL_ERROR", scope_type: "SOURCE", scope_id: "source-customer-file", status: "CANCELLED", priority: "LOW", occurrence_count: 1, version: 2, available_actions: [], created_at: "2026-07-14T09:00:00Z", updated_at: "2026-07-18T09:00:00Z", last_seen_at: "2026-07-14T09:00:00Z" },
    ],
  };
}
