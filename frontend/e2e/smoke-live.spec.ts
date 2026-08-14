/**
 * Mock'suz duman testi — gerçek backend'e giden executions ve rules sayfalarını doğrular.
 *
 * page.route KULLANMAZ; CSRF proof'u developmentFetch otomatik yönetir.
 * Amaç: 403/503 gibi entegrasyon kopukluklarını CI'da yakalamak.
 */
import { expect, test } from "@playwright/test";

test.setTimeout(60_000);

test.describe("gerçek backend duman testi", () => {
  test("executions sayfası yüklenir ve API 403/503 dönmez", async ({ page }) => {
    const failedResponses: Array<{ url: string; status: number }> = [];

    page.on("response", (response) => {
      if (
        response.url().includes("/api/v1/") &&
        (response.status() === 403 || response.status() === 503)
      ) {
        failedResponses.push({ url: response.url(), status: response.status() });
      }
    });

    await page.addInitScript(() => {
      window.localStorage.setItem("development-user-id", "dev-data-steward");
    });

    await page.goto("/executions");
    await expect(page.getByRole("heading", { level: 1, name: "Çalıştırmalar" })).toBeVisible();

    // Sayfa yüklenirken yapılan API çağrılarının tamamlanmasını bekle
    await page.waitForLoadState("networkidle");

    expect(failedResponses).toEqual([]);
  });

  test("rules sayfası yüklenir ve API 403/503 dönmez", async ({ page }) => {
    const failedResponses: Array<{ url: string; status: number }> = [];

    page.on("response", (response) => {
      if (
        response.url().includes("/api/v1/") &&
        (response.status() === 403 || response.status() === 503)
      ) {
        failedResponses.push({ url: response.url(), status: response.status() });
      }
    });

    await page.addInitScript(() => {
      window.localStorage.setItem("development-user-id", "dev-data-steward");
    });

    await page.goto("/rules");
    await expect(page.getByRole("heading", { level: 1, name: "Kurallar" })).toBeVisible();

    await page.waitForLoadState("networkidle");

    expect(failedResponses).toEqual([]);
  });

  test("bildirimler sayfası yüklenir ve API 403/503 dönmez", async ({ page }) => {
    const failedResponses: Array<{ url: string; status: number }> = [];

    page.on("response", (response) => {
      if (
        response.url().includes("/api/v1/") &&
        (response.status() === 403 || response.status() === 503)
      ) {
        failedResponses.push({ url: response.url(), status: response.status() });
      }
    });

    await page.addInitScript(() => {
      window.localStorage.setItem("development-user-id", "dev-data-steward");
    });

    await page.goto("/notifications");
    await expect(page.getByRole("heading", { level: 1, name: "Bildirimler" })).toBeVisible();

    await page.waitForLoadState("networkidle");

    expect(failedResponses).toEqual([]);
  });
});
