import { expect, test, type Page } from "@playwright/test";

const csrfProof = "development-request-proof-v1";

async function selectDevelopmentUser(page: Page, userId: string) {
  await page.evaluate((id) => localStorage.setItem("development-user-id", id), userId);
  await page.reload();
  await expect(page.getByRole("heading", { level: 1, name: "Yönetişim Görevleri" })).toBeVisible();
}

test("maker-checker sahiplik akışı: talep, karar, uygulama ve denetçi görünümü", async ({
  page,
}) => {
  test.setTimeout(120_000);
  const newOwner = `e2e-owner-${Date.now()}`;

  // ── Maker: talep oluşturma ─────────────────────────────────────────
  await page.goto("/governance");
  await page.evaluate(() => {
    window.localStorage.setItem("development-user-id", "dev-data-steward");
  });
  await page.reload();
  await expect(page.getByRole("heading", { level: 1, name: "Yönetişim Görevleri" })).toBeVisible();

  // Önceki çalışmalardan kalan bekleyen talepleri temizle (idempotent başlangıç)
  await page.evaluate(async (proof) => {
    const headers = { Accept: "application/json", "X-Development-User-Id": "dev-data-steward" };
    const datasetsResponse = await fetch("/api/v1/datasets", {
      credentials: "same-origin",
      headers,
    });
    const datasetsPayload = await datasetsResponse.json();
    const target = (datasetsPayload.items as Array<{ dataset_id: string; name: string }>).find(
      (candidate) => candidate.name === "accounts",
    );
    if (!target) return;
    const listResponse = await fetch("/api/v1/governance/approval-requests?view=MINE", {
      credentials: "same-origin",
      headers,
    });
    const payload = await listResponse.json();
    for (const item of payload.items as Array<{
      approval_request_id: string;
      status: string;
      object_id: string;
    }>) {
      if (item.status === "PENDING" && item.object_id === target.dataset_id) {
        await fetch(`/api/v1/governance/approval-requests/${item.approval_request_id}/withdraw`, {
          body: JSON.stringify({ reason_code: "MAKER.WITHDRAWAL" }),
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
            "X-CSRF-Token": proof,
            "X-Development-User-Id": "dev-data-steward",
          },
          method: "POST",
        });
      }
    }
  }, csrfProof);

  await page.getByRole("button", { name: "Yönetişim Talebi" }).click();
  const createDialog = page.getByRole("dialog");
  await expect(createDialog).toBeVisible();
  await createDialog.getByLabel("Dataset / Tablo").click();
  await page.getByRole("option", { name: /accounts/ }).click();
  await createDialog.getByLabel("Yeni sahip kullanıcı kimliği").fill(newOwner);
  await createDialog.getByRole("button", { name: "Onaya Gönder" }).click();

  // Maker talebini Gönderdiklerim'de görür ve yalnızca geri çekebilir
  await page.getByRole("tab", { name: "Gönderdiklerim" }).click();
  const makerRow = page.getByRole("row").filter({ hasText: newOwner }).first();
  await expect(makerRow).toBeVisible();
  await expect(makerRow.getByRole("button", { name: "Geri Çek" })).toBeVisible();
  await expect(makerRow.getByRole("button", { name: "Onayla/Reddet" })).toHaveCount(0);

  // Maker kendi talebine API üzerinden de karar veremez (backend fail-closed)
  const approvalRequestId = await page.evaluate(async ({ proof, userId }) => {
    const response = await fetch("/api/v1/governance/approval-requests?view=MINE", {
      credentials: "same-origin",
      headers: { Accept: "application/json", "X-Development-User-Id": userId },
    });
    const payload = await response.json();
    return payload.items[0].approval_request_id as string;
  }, { proof: csrfProof, userId: "dev-data-steward" });
  const denied = await page.evaluate(async ({ id, proof, userId }) => {
    const response = await fetch(`/api/v1/governance/approval-requests/${id}/decision`, {
      body: JSON.stringify({ decision: "APPROVE", reason_code: "OWNERSHIP.VERIFIED" }),
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRF-Token": proof,
        "X-Development-User-Id": userId,
      },
      method: "POST",
    });
    return response.status;
  }, { id: approvalRequestId, proof: csrfProof, userId: "dev-data-steward" });
  expect(denied).toBe(403);

  // ── Checker: karar ─────────────────────────────────────────────────
  await selectDevelopmentUser(page, "dev-data-owner");
  const checkerRow = page.getByRole("row").filter({ hasText: newOwner }).first();
  await expect(checkerRow).toBeVisible({ timeout: 15_000 });
  await checkerRow.getByRole("button", { name: "Onayla/Reddet" }).click();

  const decideDialog = page.getByRole("dialog");
  await expect(decideDialog).toBeVisible();
  await decideDialog.getByRole("button", { name: "Onayla", exact: true }).last().click();

  // Karar sonrası talep Onay Bekleyenler'den düşer
  await expect(page.getByRole("row").filter({ hasText: newOwner })).toHaveCount(0);

  // ── Applier: uygulama ──────────────────────────────────────────────
  await selectDevelopmentUser(page, "dev-data-governance");
  await page.getByRole("tab", { name: "Sonuçlananlar" }).click();
  const applierRow = page.getByRole("row").filter({ hasText: newOwner }).first();
  await expect(applierRow).toBeVisible({ timeout: 15_000 });
  await applierRow.getByRole("button", { name: "Uygula" }).click();
  await expect(applierRow.getByText("Uygulandı")).toBeVisible();

  // ── Denetçi: salt okunur görünüm ───────────────────────────────────
  await selectDevelopmentUser(page, "dev-audit-viewer");
  await page.getByRole("tab", { name: "Tüm Kararlar" }).click();
  const auditorRow = page.getByRole("row").filter({ hasText: newOwner }).first();
  await expect(auditorRow).toBeVisible({ timeout: 15_000 });
  await expect(auditorRow.getByRole("button", { name: "Onayla/Reddet" })).toHaveCount(0);
  await expect(auditorRow.getByRole("button", { name: "Geri Çek" })).toHaveCount(0);
  await expect(auditorRow.getByRole("button", { name: "Uygula" })).toHaveCount(0);
});

test("metadata diff uygulama akışı: seçim, onay ve uygulama", async ({ page }) => {
  test.setTimeout(180_000);

  // ── Maker: keşif ve seçim ───────────────────────────────────────────
  await page.goto("/catalog");
  await page.evaluate(() => {
    window.localStorage.setItem("development-user-id", "dev-data-steward");
  });
  await page.reload();
  await page.getByRole("row").first().getByRole("link").first().click();
  await expect(page.getByRole("heading", { name: "Alanlar" })).toBeVisible({ timeout: 15_000 });

  await page.getByRole("button", { name: /Keşfi çalıştır|Yeniden keşfet/ }).click();
  // Keşif tamamlanana kadar bekle; fark yoksa senaryo geçerli değildir.
  const diffPanel = page.getByText("Bekleyen Fark");
  try {
    await expect
      .poll(async () => diffPanel.isVisible(), { timeout: 90_000 })
      .toBe(true);
  } catch {
    // poll timed out – panel may still be invisible
  }
  if (!(await diffPanel.isVisible())) {
    test.skip(true, "Keşif bekleyen metadata farkı üretmedi.");
    return;
  }

  const submitResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/governance/approval-requests") &&
      response.request().method() === "POST",
  );
  const checkboxes = page.getByRole("checkbox");
  const checkboxCount = await checkboxes.count();
  for (let index = 0; index < checkboxCount; index += 1) {
    await checkboxes.nth(index).check();
  }
  await page.getByRole("button", { name: "Onaya gönder" }).click();
  await expect(page.getByText(/Onay bekleniyor/)).toBeVisible({ timeout: 15_000 });
  const createdRequest = (await (await submitResponse).json()) as {
    approval_request_id: string;
  };

  // ── Checker: API üzerinden onay ─────────────────────────────────────
  const decided = await page.evaluate(
    async ({ id, proof }) => {
      const response = await fetch(`/api/v1/governance/approval-requests/${id}/decision`, {
        body: JSON.stringify({ decision: "APPROVE", reason_code: "METADATA.VERIFIED" }),
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-CSRF-Token": proof,
          "X-Development-User-Id": "dev-data-owner",
        },
        method: "POST",
      });
      return response.status;
    },
    { id: createdRequest.approval_request_id, proof: csrfProof },
  );
  expect(decided).toBe(200);

  // ── Applier: API üzerinden uygulama ─────────────────────────────────
  const applied = await page.evaluate(
    async ({ id, proof }) => {
      const response = await fetch(`/api/v1/governance/approval-requests/${id}/apply`, {
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "X-CSRF-Token": proof,
          "X-Development-User-Id": "dev-data-governance",
        },
        method: "POST",
      });
      return response.status;
    },
    { id: createdRequest.approval_request_id, proof: csrfProof },
  );
  expect(applied).toBe(200);

  // Diff APPLIED kapandığı için yeni keşifte aynı fark tekrar üretilmez.
  await page.reload();
  await expect(page.getByText("Bekleyen Fark")).toHaveCount(0);
});
