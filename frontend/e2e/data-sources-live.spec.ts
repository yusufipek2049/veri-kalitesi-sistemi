import { expect, test, type Page } from "@playwright/test";

const sourceHost = process.env.DQ_E2E_SOURCE_HOST ?? "postgres";
const sourcePort = process.env.DQ_E2E_SOURCE_PORT ?? "5432";
const sourceDatabase = process.env.DQ_E2E_SOURCE_DATABASE ?? "data_quality";
const sourceSchema = process.env.DQ_E2E_SOURCE_SCHEMA ?? "dq";
const secretReference = process.env.DQ_E2E_SECRET_REFERENCE ?? "secret://local/e2e-source";
const sourceRootCertificate = process.env.DQ_E2E_SOURCE_ROOT_CERT
  ?? "/run/postgres-tls/server.crt";
const csrfProof = "development-request-proof-v1";

async function selectDevelopmentUser(page: Page, userId: string) {
  await page.evaluate((id) => localStorage.setItem("development-user-id", id), userId);
  await page.reload();
}

async function directCommand(
  page: Page,
  userId: string,
  path: string,
  body?: Record<string, unknown>,
) {
  return page.evaluate(async ({ commandBody, commandPath, developmentUserId, proof }) => {
    const response = await fetch(commandPath, {
      body: commandBody === undefined ? undefined : JSON.stringify(commandBody),
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRF-Token": proof,
        "X-Development-User-Id": developmentUserId,
      },
      method: "POST",
    });
    return { body: await response.json(), status: response.status };
  }, { commandBody: body, commandPath: path, developmentUserId: userId, proof: csrfProof });
}

test("gerçek PostgreSQL yolunda create-test-activation-passivation ve audit zinciri", async ({
  page,
}) => {
  test.setTimeout(90_000);
  const sourceName = `E2E PostgreSQL ${Date.now()}`;

  await page.addInitScript(() => {
    window.localStorage.setItem("development-user-id", "dev-data-steward-owner");
  });
  await page.goto("/data-sources");
  await expect(page.getByRole("heading", { level: 1, name: "Veri Kaynakları" })).toBeVisible();

  await page.getByRole("button", { name: "Yeni veri kaynağı" }).click();
  await page.getByLabel("Kaynak adı").fill(sourceName);
  await page.getByLabel("Sunucu").fill(sourceHost);
  await page.getByLabel("Port").fill(sourcePort);
  await page.getByLabel("Veritabanı").fill(sourceDatabase);
  await page.getByLabel("Şema").fill(sourceSchema);
  await page.getByLabel("Secret referansı").fill(secretReference);
  await page.getByLabel("Ek bağlantı parametreleri (JSON)").fill(JSON.stringify({
    ssl_root_cert: sourceRootCertificate,
  }));
  await page.getByRole("button", { name: "Kaydet" }).click();

  const row = page.getByRole("listitem").filter({ hasText: sourceName });
  await expect(row).toBeVisible();

  // Yeni UUID'nin dev identity adapter tarafından açık scope'a eklenmesini yeniden oku.
  await page.getByRole("button", { name: "Yenile" }).click();
  await expect(row.getByRole("button", { name: "Bağlantıyı test et" })).toBeVisible();
  await row.getByRole("button", { name: "Bağlantıyı test et" }).click();
  await expect(row.getByText("Test Başarılı")).toBeVisible();

  const activationResponsePromise = page.waitForResponse(
    (response) => response.request().method() === "POST"
      && response.url().includes("/activation"),
  );
  await row.getByRole("button", { name: "Aktivasyon talep et" }).click();
  const activationResponse = await activationResponsePromise;
  expect(activationResponse.status()).toBe(201);
  const activationBody = await activationResponse.json() as {
    item: { data_source_id: string; pending_activation_request_id: string };
  };
  const sourceId = activationBody.item.data_source_id;
  const activationRequestId = activationBody.item.pending_activation_request_id;
  expect(activationRequestId).toBeTruthy();

  const makerDecision = await directCommand(
    page,
    "dev-data-steward-owner",
    `/api/v1/data-source-activation-requests/${encodeURIComponent(activationRequestId)}/decision`,
    { decision: "APPROVE", reason_code: "E2E_SELF_DECISION" },
  );
  expect(makerDecision.status).toBe(403);
  expect(makerDecision.body).toMatchObject({
    code: "DATA_SOURCE_MAKER_CHECKER_VIOLATION",
  });

  await selectDevelopmentUser(page, "dev-data-owner");
  const ownerRow = page.getByRole("listitem").filter({ hasText: sourceName });
  await expect(ownerRow.getByRole("button", { name: "Onayla" })).toBeVisible();
  await ownerRow.getByRole("button", { name: "Onayla" }).click();
  await page.getByLabel("Karar gerekçe kodu").fill("E2E_APPROVED");
  await page.getByRole("button", { name: "Kararı gönder" }).click();
  await expect(ownerRow.getByText("Aktif")).toBeVisible();

  await ownerRow.getByRole("button", { name: "Pasifleştir" }).click();
  await page.getByLabel("Gerekçe kodu").fill("E2E_PASSIVATED");
  await page.getByRole("button", { name: "Pasifleştir", exact: true }).click();
  await expect(ownerRow.getByText("Pasif")).toBeVisible();

  const scopeDenied = await directCommand(
    page,
    "dev-limited-steward",
    `/api/v1/data-sources/${encodeURIComponent(sourceId)}/test`,
  );
  expect(scopeDenied.status).toBe(403);
  expect(scopeDenied.body).toMatchObject({ code: "DATA_SOURCE_PERMISSION_DENIED" });

  await selectDevelopmentUser(page, "dev-audit-viewer");
  const auditResponse = await page.evaluate(async (objectId) => {
    const response = await fetch(
      `/api/v1/audit/events?days=1&object_type=DataSource&page_size=100`,
      {
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "X-Development-User-Id": "dev-audit-viewer",
        },
      },
    );
    const body = await response.json() as {
      integrity_valid: boolean;
      items: Array<{ action: string; object_id: string; result: string }>;
    };
    return {
      integrityValid: body.integrity_valid,
      matchingActions: body.items
        .filter((item) => item.object_id === objectId)
        .map((item) => `${item.action}:${item.result}`),
      status: response.status,
    };
  }, sourceId);
  expect(auditResponse.status).toBe(200);
  expect(auditResponse.integrityValid).toBe(true);
  expect(auditResponse.matchingActions).toEqual(expect.arrayContaining([
    "DATA_SOURCE_CREATED:SUCCESS",
    "DATA_SOURCE_CONNECTION_TESTED:SUCCESS",
    "DATA_SOURCE_ACTIVATION_REQUESTED:SUCCESS",
    "DATA_SOURCE_ACTIVATION_DECIDED:SUCCESS",
    "DATA_SOURCE_DEACTIVATED:SUCCESS",
  ]));

  const deniedAuditResponse = await page.evaluate(async (requestId) => {
    const response = await fetch(
      `/api/v1/audit/events?days=1&action=DATA_SOURCE_ACTIVATION_DECISION_DENIED&page_size=100`,
      {
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "X-Development-User-Id": "dev-audit-viewer",
        },
      },
    );
    const body = await response.json() as {
      items: Array<{ object_id: string; reason_code: string; result: string }>;
    };
    return {
      found: body.items.some((item) => item.object_id === requestId
        && item.reason_code === "MAKER_CHECKER_VIOLATION"
        && item.result === "DENIED"),
      status: response.status,
    };
  }, activationRequestId);
  expect(deniedAuditResponse.status).toBe(200);
  expect(deniedAuditResponse.found).toBe(true);
});
