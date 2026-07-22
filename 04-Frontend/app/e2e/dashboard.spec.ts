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
});

for (const viewport of viewports) {
  test(`dashboard ${viewport.name} görünümünde taşma üretmez`, async ({ page }, testInfo) => {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1, name: "Genel Bakış" })).toBeVisible();
    await expect(page.getByText("SENTETİK VERİ")).toBeVisible();
    await expect(page.getByRole("img", { name: /Resmî nihai skor trendi/ })).toBeVisible();

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);

    await page.screenshot({
      path: testInfo.outputPath(`dashboard--normal--${viewport.name}.png`),
      fullPage: true,
    });
  });
}

test("grafik ve erişilebilir tablo aynı gözlemleri kullanır", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Tablo" }).click();

  const table = page.getByRole("table", { name: "Veri kalitesi trend tablosu" });
  await expect(table).toBeVisible();
  await expect(table.getByRole("row")).toHaveCount(9);
  await expect(table.getByText("Dışlandı")).toHaveCount(2);
});

test("klavye odağı görünür ve yetkisiz yüzey veri ifşa etmez", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/?state=unauthorized");

  for (let attempt = 0; attempt < 4; attempt += 1) {
    await page.keyboard.press("Tab");
    const hasButtonFocus = await page.evaluate(() => document.activeElement?.tagName === "BUTTON");
    if (hasButtonFocus) break;
  }

  const focusedElement = await page.evaluate(() => ({
    name: document.activeElement?.getAttribute("aria-label") ?? document.activeElement?.textContent,
    outline: getComputedStyle(document.activeElement as Element).outlineStyle,
  }));
  expect(focusedElement.name?.trim()).toBeTruthy();
  expect(focusedElement.outline).not.toBe("none");
  await expect(page.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();
  await expect(page.getByText("Nihai Kalite Skoru")).not.toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("dashboard--unauthorized--1366x768.png"),
    fullPage: true,
  });
});
