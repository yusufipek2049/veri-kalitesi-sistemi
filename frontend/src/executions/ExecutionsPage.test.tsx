import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { ExecutionsPage } from "./ExecutionsPage";
import type { ExecutionDetail, ExecutionListItem } from "./model";

function renderPage() {
  return render(<ThemeModeProvider><MemoryRouter initialEntries={["/executions"]}><ExecutionsPage /></MemoryRouter></ThemeModeProvider>);
}

describe("Çalıştırmalar ekranı", () => {
  it("teknik hata, kısmi ve başarılı durumları ayrı gösterir", () => {
    renderPage();
    expect(screen.getByRole("heading", { level: 1, name: "Çalıştırmalar" })).toBeVisible();
    expect(screen.getAllByTestId("execution-icon-slot")).toHaveLength(8);
    expect(screen.getByLabelText("Durum: Teknik hata")).toBeVisible();
    expect(screen.getByLabelText("Durum: Kısmi")).toBeVisible();
    expect(screen.getByLabelText("Durum: Teknik olarak tamamlandı")).toBeVisible();
  });

  it("metin ve durum filtrelerini uygular", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Çalıştırma ara"), { target: { value: "timeout" } });
    expect(screen.getByText("execution-timeout")).toBeVisible();
    expect(screen.queryByText("execution-running")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Çalıştırma ara"), { target: { value: "" } });
    fireEvent.mouseDown(screen.getByLabelText("Durum"));
    fireEvent.click(screen.getByRole("option", { name: "Kısmi" }));
    expect(screen.getByText("execution-partial")).toBeVisible();
    expect(screen.queryByText("execution-success")).not.toBeInTheDocument();
  });

  it("yetkisiz durumda filtre veya geçmiş verisi göstermez", () => {
    render(<ThemeModeProvider><MemoryRouter><ExecutionsPage state="unauthorized" /></MemoryRouter></ThemeModeProvider>);
    expect(screen.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();
    expect(screen.queryByLabelText("Çalıştırma ara")).not.toBeInTheDocument();
    expect(screen.queryByText("execution-running")).not.toBeInTheDocument();
  });

  it("shadow yürütmeyi yaşam döngüsü durumundan ayrı etiketler", () => {
    const items: ExecutionListItem[] = [{
      id: "execution-shadow",
      executionType: "MANUAL",
      executionMode: "SHADOW",
      status: "SUCCESS",
      workloadClass: "LIGHT",
      ruleCount: 1,
      sourceCount: 1,
      attemptCount: 1,
      progressPercent: 100,
      availableActions: [],
      datasets: [],
      createdAt: "2026-07-23T09:00:00Z",
    }];
    render(<ThemeModeProvider><MemoryRouter><ExecutionsPage items={items} /></MemoryRouter></ThemeModeProvider>);
    expect(screen.getByLabelText("Durum: SHADOW")).toBeVisible();
    expect(screen.getByLabelText("Durum: Teknik olarak tamamlandı")).toBeVisible();
  });

  it("eski tamamlanmış kaydı başlamadı diye göstermez", () => {
    const items: ExecutionListItem[] = [{
      id: "execution-legacy-success",
      executionType: "MANUAL",
      status: "SUCCESS",
      workloadClass: "LIGHT",
      ruleCount: 1,
      sourceCount: 1,
      attemptCount: 1,
      progressPercent: 100,
      availableActions: [],
      datasets: [],
      createdAt: "2026-07-23T09:00:00Z",
      finishedAt: "2026-07-23T09:01:00Z",
    }];
    render(<ThemeModeProvider><MemoryRouter><ExecutionsPage items={items} /></MemoryRouter></ThemeModeProvider>);
    expect(screen.getByText("Başlangıç kaydı yok")).toBeVisible();
    expect(screen.queryByText("Henüz başlamadı")).not.toBeInTheDocument();
  });

  it("engellenmiş yürütmeyi kilit ikonu ve nedeni ile gösterir", () => {
    const items: ExecutionListItem[] = [{
      id: "execution-blocked",
      executionType: "MANUAL",
      status: "BLOCKED",
      workloadClass: "HEAVY",
      ruleCount: 1,
      sourceCount: 1,
      attemptCount: 0,
      progressPercent: 0,
      blockedReasonCode: "SOURCE_LOCKED",
      availableActions: [],
      datasets: [],
      createdAt: "2026-07-23T09:00:00Z",
    }];
    render(<ThemeModeProvider><MemoryRouter><ExecutionsPage items={items} /></MemoryRouter></ThemeModeProvider>);
    expect(screen.getByLabelText("Durum: Engellenmiş")).toBeVisible();
    expect(screen.getByText("Engellendi: SOURCE_LOCKED")).toBeVisible();
  });

  it("çalışan yürütmede ilerleme çubuğu gösterir", () => {
    const items: ExecutionListItem[] = [{
      id: "execution-progress",
      executionType: "MANUAL",
      status: "RUNNING",
      workloadClass: "LIGHT",
      ruleCount: 1,
      sourceCount: 1,
      attemptCount: 1,
      progressPercent: 65,
      availableActions: ["cancel"],
      datasets: [{ datasetId: "ds-tx", name: "transactions", namespace: "public", sourceId: "src-core", sourceName: "Core DB" }],
      createdAt: "2026-07-23T09:00:00Z",
      startedAt: "2026-07-23T09:01:00Z",
    }];
    render(<ThemeModeProvider><MemoryRouter><ExecutionsPage items={items} /></MemoryRouter></ThemeModeProvider>);
    const progressbar = screen.getByRole("progressbar");
    expect(progressbar).toBeVisible();
  });

  it("dataset isimlerini ve schedule bilgisini gosterir", () => {
    const items: ExecutionListItem[] = [{
      id: "execution-with-datasets",
      executionType: "SCHEDULED",
      status: "SUCCESS",
      workloadClass: "LIGHT",
      ruleCount: 1,
      sourceCount: 1,
      attemptCount: 1,
      progressPercent: 100,
      availableActions: [],
      datasets: [{ datasetId: "ds-tx", name: "transactions", namespace: "public", sourceId: "src-core", sourceName: "Core DB" }],
      scheduleId: "schedule-daily-tx",
      createdAt: "2026-07-23T09:00:00Z",
      startedAt: "2026-07-23T09:01:00Z",
      finishedAt: "2026-07-23T09:10:00Z",
    }];
    render(<ThemeModeProvider><MemoryRouter><ExecutionsPage items={items} /></MemoryRouter></ThemeModeProvider>);
    expect(screen.getByText("transactions (public) @ Core DB")).toBeVisible();
    expect(screen.getByText("Zamanlanmış: schedule-daily-tx")).toBeVisible();
  });

  it("baslatma dialog'u dropdown alanlari ve otomatik idempotency anahtari gosterir", () => {
    const onStart = vi.fn();
    const ruleOptions = [{ ruleVersionId: "rv-1", label: "Müşteri KYK (v3)" }];
    const sourceOptions = [{ sourceId: "src-1", label: "Core DB" }];
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <ExecutionsPage
            onStart={onStart}
            ruleOptions={ruleOptions}
            sourceOptions={sourceOptions}
          />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    fireEvent.click(screen.getByText("Çalıştırma başlat"));
    expect(screen.getByRole("combobox", { name: /kural/i })).toBeVisible();
    expect(screen.getByRole("combobox", { name: /kaynak/i })).toBeVisible();
    const idempotencyField = screen.getByLabelText(/idempotency anahtarı/i);
    expect(idempotencyField).toBeVisible();
    expect((idempotencyField as HTMLInputElement).value).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
    );
  });

  it("kural seçilince yalnızca ilişkili kaynak seçilebilir ve otomatik seçilir", () => {
    const onStart = vi.fn();
    const ruleOptions = [{
      ruleVersionId: "rv-1",
      label: "IBAN boş olamaz (v1)",
      datasetId: "ds-1",
      datasetLabel: "public.accounts",
      sourceId: "src-1",
    }];
    const sourceOptions = [
      { sourceId: "src-1", label: "Core DB" },
      { sourceId: "src-2", label: "Risk DB" },
    ];
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <ExecutionsPage
            onStart={onStart}
            ruleOptions={ruleOptions}
            sourceOptions={sourceOptions}
          />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    fireEvent.click(screen.getByText("Çalıştırma başlat"));

    // Kuralı seç
    fireEvent.mouseDown(screen.getByRole("combobox", { name: /kural/i }));
    fireEvent.click(screen.getByRole("option", { name: "IBAN boş olamaz (v1)" }));

    // İlişkili dataset chip'i görünür ve ilişkili kaynak otomatik seçilir
    expect(screen.getByText("public.accounts")).toBeVisible();
    const sourceInput = screen.getByRole("combobox", { name: /kaynak/i });
    expect(sourceInput).toHaveValue("Core DB");

    // İlişkisiz kaynak seçeneklerde yer almaz
    fireEvent.mouseDown(sourceInput);
    expect(screen.queryByRole("option", { name: "Risk DB" })).not.toBeInTheDocument();
    fireEvent.keyDown(sourceInput, { key: "Escape" });

    // Başlatma ilişkili kaynakla yapılır
    fireEvent.click(screen.getByRole("button", { name: "Başlat" }));
    expect(onStart).toHaveBeenCalledWith(["rv-1"], ["src-1"], expect.any(String));
  });

  it("kural seçilmeden kaynak alanı kapalıdır ve başlatma yapılamaz", () => {
    const onStart = vi.fn();
    const sourceOptions = [{ sourceId: "src-1", label: "Core DB" }];
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <ExecutionsPage onStart={onStart} sourceOptions={sourceOptions} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    fireEvent.click(screen.getByText("Çalıştırma başlat"));

    expect(screen.getByRole("combobox", { name: /kaynak/i })).toBeDisabled();
    const idempotencyField = screen.getByLabelText(/idempotency anahtarı/i);
    expect(screen.getByRole("button", { name: "Başlat" })).toBeDisabled();
    expect(idempotencyField).toBeVisible();
  });

  it("detay dialog'unda job bilgilerini gosterir", () => {
    const detail: ExecutionDetail = {
      item: {
        id: "execution-job-detail",
        executionType: "MANUAL",
        status: "RUNNING",
        workloadClass: "LIGHT",
        ruleCount: 1,
        sourceCount: 1,
        attemptCount: 2,
        progressPercent: 50,
        availableActions: ["cancel"],
        datasets: [],
        createdAt: "2026-07-23T09:00:00Z",
        startedAt: "2026-07-23T09:01:00Z",
      },
      results: [],
      ruleDefinitions: [],
      jobInfo: {
        jobId: "execution-job-detail",
        status: "RUNNING",
        queuePosition: null,
        workerId: "worker-a",
        leasedUntil: "2026-07-23T09:06:00Z",
        attemptCount: 2,
        lastErrorClass: null,
        completedAt: null,
        completionOutcome: null,
      },
    };
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <ExecutionsPage detailOpen executionDetail={detail} onCloseDetail={() => {}} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    expect(screen.getByText("Job Bilgileri")).toBeVisible();
    expect(screen.getAllByText("execution-job-detail").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("worker-a")).toBeVisible();
  });

  it("teknik olarak tamamlanan çalıştırmadaki kalite başarısızlığını açıklar", () => {
    const detail: ExecutionDetail = {
      item: {
        id: "execution-quality-failed",
        executionType: "MANUAL",
        status: "SUCCESS",
        workloadClass: "LIGHT",
        ruleCount: 1,
        sourceCount: 1,
        attemptCount: 1,
        progressPercent: 100,
        availableActions: [],
        datasets: [],
        createdAt: "2026-07-23T09:00:00Z",
        startedAt: "2026-07-23T09:00:01Z",
        finishedAt: "2026-07-23T09:00:02Z",
      },
      results: [{
        ruleVersionId: "rv-failed",
        populationCount: 30_000,
        passedCount: 25_408,
        failedCount: 4_592,
        evaluatedCount: 30_000,
        measurementStatus: "Failed",
      }],
      ruleDefinitions: [],
      jobInfo: null,
    };
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <ExecutionsPage detailOpen executionDetail={detail} onCloseDetail={() => {}} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    expect(screen.getByText(/en az bir kalite kuralı başarısız oldu/i)).toBeVisible();
    expect(screen.getByLabelText("Durum: Başarısız")).toBeVisible();
  });

  it("onAdhocSql verildiginde 'Ozel SQL' butonu gosterir", () => {
    const onAdhocSql = vi.fn();
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <ExecutionsPage onAdhocSql={onAdhocSql} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    expect(screen.getByText("Özel SQL")).toBeVisible();
  });

  it("onAdhocSql yoksa 'Ozel SQL' butonu gostermez", () => {
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <ExecutionsPage />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    expect(screen.queryByText("Özel SQL")).not.toBeInTheDocument();
  });

  it("Ozel SQL dialog'u SQL editor, kaynak, zaman asimi ve satir limiti alanlarini gosterir", () => {
    const onAdhocSql = vi.fn();
    const sourceOptions = [{ sourceId: "src-1", label: "Core DB" }];
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <ExecutionsPage onAdhocSql={onAdhocSql} sourceOptions={sourceOptions} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    fireEvent.click(screen.getByText("Özel SQL"));
    expect(screen.getByText("Özel SQL Çalıştır")).toBeVisible();
    expect(screen.getByPlaceholderText(/Salt okunur SQL/)).toBeVisible();
    expect(screen.getByRole("combobox", { name: /kaynak/i })).toBeVisible();
    expect(screen.getByDisplayValue("30")).toBeVisible();
    expect(screen.getByDisplayValue("1000")).toBeVisible();
  });

  it("Ozel SQL dialog'unda bos SQL ile submit engellenir", async () => {
    const onAdhocSql = vi.fn();
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <ExecutionsPage onAdhocSql={onAdhocSql} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    fireEvent.click(screen.getByText("Özel SQL"));
    // Submit button should be disabled when SQL is empty
    const submitBtn = screen.getByText("Çalıştır").closest("button");
    expect(submitBtn).toBeDisabled();
    expect(onAdhocSql).not.toHaveBeenCalled();
  });

  it("Ozel SQL dialog'unda SELECT ile baslamayan SQL hata verir", async () => {
    const onAdhocSql = vi.fn();
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <ExecutionsPage onAdhocSql={onAdhocSql} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    fireEvent.click(screen.getByText("Özel SQL"));
    fireEvent.change(screen.getByPlaceholderText(/Salt okunur SQL/), { target: { value: "INSERT INTO x VALUES (1)" } });
    fireEvent.click(screen.getByText("Çalıştır"));
    await waitFor(() => {
      expect(screen.getByText("SQL sorgusu SELECT ile başlamalıdır.")).toBeVisible();
    });
    expect(onAdhocSql).not.toHaveBeenCalled();
  });

  it("Ozel SQL dialog'nda yasak keyword iceren SQL hata verir", async () => {
    const onAdhocSql = vi.fn();
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <ExecutionsPage onAdhocSql={onAdhocSql} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    fireEvent.click(screen.getByText("Özel SQL"));
    fireEvent.change(screen.getByPlaceholderText(/Salt okunur SQL/), { target: { value: "SELECT * FROM t; DROP TABLE x" } });
    fireEvent.click(screen.getByText("Çalıştır"));
    await waitFor(() => {
      expect(screen.getByText(/DROP içermemelidir/)).toBeVisible();
    });
    expect(onAdhocSql).not.toHaveBeenCalled();
  });

  it("Gecerli SQL ile submit onAdhocSql'i dogru parametrelerle cagirir", async () => {
    const onAdhocSql = vi.fn().mockResolvedValue(undefined);
    render(
      <ThemeModeProvider>
        <MemoryRouter>
          <ExecutionsPage onAdhocSql={onAdhocSql} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    fireEvent.click(screen.getByText("Özel SQL"));
    fireEvent.change(screen.getByPlaceholderText(/Salt okunur SQL/), { target: { value: "SELECT * FROM customers WHERE email IS NULL" } });
    fireEvent.click(screen.getByText("Çalıştır"));
    await waitFor(() => {
      expect(onAdhocSql).toHaveBeenCalledWith(
        "SELECT * FROM customers WHERE email IS NULL",
        [],
        30,
        1000,
      );
    });
  });
});
