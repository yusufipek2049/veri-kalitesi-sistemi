import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { JobsPage } from "./JobsPage";
import { CreateJobDialog, type JobDatasetOption, type JobRuleOption } from "./dialogs/CreateJobDialog";
import type { JobItem, ScheduleCreatePayload } from "./model";

afterEach(() => vi.unstubAllGlobals());

const baseJob: JobItem = {
  id: "sch-1",
  name: "Hesap mutabakat job'u",
  scheduleType: "INTERVAL",
  timezoneName: "Europe/Istanbul",
  ruleVersionIds: ["rv-1"],
  createdBy: "user-1",
  localTime: null,
  dayOfWeek: null,
  dayOfMonth: null,
  intervalMinutes: 10,
  isActive: true,
  nextRunAt: "2026-08-17T09:10:00Z",
  createdAt: "2026-08-16T12:00:00Z",
  lastTriggeredAt: null,
};

function renderPage(props: Partial<Parameters<typeof JobsPage>[0]> = {}) {
  return render(
    <ThemeModeProvider>
      <MemoryRouter>
        <JobsPage datasetInfoByJob={{}} items={[baseJob]} {...props} />
      </MemoryRouter>
    </ThemeModeProvider>,
  );
}

describe("Jobs ekranı", () => {
  it("job satırını özet, nitelik rozeti ve aksiyonla gösterir", () => {
    renderPage({
      datasetInfoByJob: { "sch-1": { label: "public.accounts", nature: "NEAR_TIME" } },
    });
    expect(screen.getByRole("heading", { level: 1, name: "Jobs" })).toBeVisible();
    expect(screen.getByText("Hesap mutabakat job'u")).toBeVisible();
    expect(screen.getByText("public.accounts")).toBeVisible();
    expect(screen.getByText("10 dakikada bir")).toBeVisible();
    expect(screen.getByText("Yakın Zamanlı")).toBeVisible();
    expect(screen.getByText("AKTİF")).toBeVisible();
    expect(screen.getByText("1 job")).toBeVisible();
  });

  it("dataset bilgisi çözülemeyen job için nitelik rozetini boş gösterir", () => {
    renderPage();
    expect(screen.getByText("Nitelik yok")).toBeVisible();
    expect(screen.getByText("—")).toBeVisible();
  });

  it("aktif job'u pasifleştirme eylemini iletir", () => {
    const onToggleActive = vi.fn();
    renderPage({ onToggleActive });
    fireEvent.click(screen.getByRole("button", { name: "Pasifleştir" }));
    expect(onToggleActive).toHaveBeenCalledWith("sch-1", false);
  });

  it("boş durumda yönlendirme mesajı gösterir", () => {
    renderPage({ state: "empty", items: [] });
    expect(
      screen.getByText("Henüz tanımlı job yok. Tablo niteliğine uygun ilk zamanlayıcıyı oluşturun."),
    ).toBeVisible();
  });

  it("hata durumunda izleme kodunu gösterir", () => {
    renderPage({ state: "error", items: [], correlationId: "c-jobs-error" });
    expect(screen.getByText("İzleme kodu: c-jobs-error.")).toBeVisible();
  });
});

const datasets: JobDatasetOption[] = [
  { id: "ds-near", label: "public.accounts", nature: "NEAR_TIME" },
  { id: "ds-plain", label: "public.logs", nature: null },
];

const rules: JobRuleOption[] = [
  { ruleVersionId: "rv-1", label: "Tutarlılık (v1)", datasetId: "ds-near" },
];

const proposalsBody = {
  api_version: "v1",
  data_origin: "test",
  correlation_id: "c-prop",
  dataset_id: "ds-near",
  timeliness_nature: "NEAR_TIME",
  band: "INTERVAL 5-15 dakika",
  proposals: [
    { schedule_type: "INTERVAL", interval_minutes: 5, label: "5 dakikada bir" },
    { schedule_type: "INTERVAL", interval_minutes: 10, label: "10 dakikada bir" },
    { schedule_type: "INTERVAL", interval_minutes: 15, label: "15 dakikada bir" },
  ],
};

interface DialogHarnessProps {
  onCreate?: (payload: ScheduleCreatePayload) => void;
  onSubmitGovernance?: (payload: { datasetId: string; schedule: ScheduleCreatePayload }) => void;
  governanceForced?: boolean;
}

function renderDialog(props: DialogHarnessProps = {}) {
  return render(
    <ThemeModeProvider>
      <MemoryRouter>
        <CreateJobDialog
          datasets={datasets}
          error={null}
          governanceForced={props.governanceForced ?? false}
          governanceResult={null}
          governanceSubmitting={false}
          onClose={() => undefined}
          onCreate={props.onCreate ?? (() => undefined)}
          onSubmitGovernance={props.onSubmitGovernance ?? (() => undefined)}
          open
          rules={rules}
          submitting={false}
        />
      </MemoryRouter>
    </ThemeModeProvider>,
  );
}

async function selectDataset(label: string) {
  fireEvent.mouseDown(screen.getByRole("combobox", { name: "Dataset" }));
  fireEvent.click(await screen.findByRole("option", { name: label }));
}

async function selectRule(label: string) {
  fireEvent.mouseDown(screen.getByRole("combobox", { name: "Kural sürümleri" }));
  fireEvent.click(await screen.findByRole("option", { name: label }));
  // Çoklu seçim menüsü açık kalır; erişilebilirlik ağacını kilitlememesi için kapat.
  fireEvent.keyDown(screen.getByRole("listbox", { name: "Kural sürümleri" }), { key: "Escape" });
}

describe("Yeni Job iletişim kutusu", () => {
  it("niteliği olmayan dataset için uyarı gösterir ve oluşturmayı engeller", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ ...proposalsBody, dataset_id: "ds-plain", timeliness_nature: null, band: null, proposals: [] }),
          { status: 200 },
        ),
      ),
    );
    renderDialog();
    await selectDataset("public.logs");
    expect(
      screen.getByText(/zamanlılık niteliği atanmamış/),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Job Oluştur" })).toBeDisabled();
  });

  it("dataset seçilince nitelik rozetini ve öneri chip'lerini gösterir", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(proposalsBody), { status: 200 })),
    );
    renderDialog();
    await selectDataset("public.accounts");

    expect(await screen.findByText("Nitelik: Yakın Zamanlı")).toBeVisible();
    expect(screen.getByText("Önerilen bant: INTERVAL 5-15 dakika")).toBeVisible();
    const chips = await screen.findAllByText(/dakikada bir/);
    expect(chips.length).toBeGreaterThanOrEqual(3);
  });

  it("öneri chip'i aralığı forma uygular ve doğrudan oluşturma yapar", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(proposalsBody), { status: 200 })),
    );
    const onCreate = vi.fn();
    renderDialog({ onCreate });
    await selectDataset("public.accounts");
    await screen.findByText("Önerilen bant: INTERVAL 5-15 dakika");
    await selectRule("Tutarlılık (v1)");

    fireEvent.change(screen.getByLabelText(/Job adı/), { target: { value: "Mutabakat job'u" } });
    const chip = (await screen.findAllByText("10 dakikada bir")).find(
      (element) => element.closest("[role='button']"),
    );
    fireEvent.click(chip as HTMLElement);

    fireEvent.click(screen.getByRole("button", { name: "Job Oluştur" }));
    expect(onCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "Mutabakat job'u",
        dataset_id: "ds-near",
        schedule_type: "INTERVAL",
        interval_minutes: 10,
        rule_version_ids: ["rv-1"],
        timezone_name: "Europe/Istanbul",
      }),
    );
  });

  it("bant dışı aralıkta yönetişim talebi akışına geçer", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(proposalsBody), { status: 200 })),
    );
    const onCreate = vi.fn();
    const onSubmitGovernance = vi.fn();
    renderDialog({ onCreate, onSubmitGovernance });
    await selectDataset("public.accounts");
    await screen.findByText("Önerilen bant: INTERVAL 5-15 dakika");
    await selectRule("Tutarlılık (v1)");

    fireEvent.change(screen.getByLabelText(/Job adı/), { target: { value: "Sık mutabakat" } });
    fireEvent.change(screen.getByLabelText(/Aralık \(dakika\)/), { target: { value: "30" } });

    expect(
      screen.getByText(/Seçilen aralık önerilen bandın dışında/),
    ).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Onay Talebi Aç" }));
    expect(onSubmitGovernance).toHaveBeenCalledWith({
      datasetId: "ds-near",
      schedule: expect.objectContaining({
        schedule_type: "INTERVAL",
        interval_minutes: 30,
        rule_version_ids: ["rv-1"],
      }),
    });
    expect(onCreate).not.toHaveBeenCalled();
  });

  it("sunucu 409 sonrası governance zorlandığında bant içi seçimde bile talep açar", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(proposalsBody), { status: 200 })),
    );
    const onSubmitGovernance = vi.fn();
    renderDialog({ governanceForced: true, onSubmitGovernance });
    await selectDataset("public.accounts");
    await screen.findByText("Önerilen bant: INTERVAL 5-15 dakika");
    await selectRule("Tutarlılık (v1)");

    fireEvent.change(screen.getByLabelText(/Job adı/), { target: { value: "Zorunlu talep" } });
    const chip = (await screen.findAllByText("10 dakikada bir")).find(
      (element) => element.closest("[role='button']"),
    );
    fireEvent.click(chip as HTMLElement);

    fireEvent.click(screen.getByRole("button", { name: "Onay Talebi Aç" }));
    expect(onSubmitGovernance).toHaveBeenCalledWith(
      expect.objectContaining({ datasetId: "ds-near" }),
    );
  });
});

describe("Jobs listesi nitelik rozeti tonları", () => {
  it("her nitelik için görünür rozet üretir", () => {
    const { unmount } = renderPage({
      datasetInfoByJob: { "sch-1": { label: "public.trades", nature: "REAL_TIME" } },
    });
    expect(screen.getByText("Anlık")).toBeVisible();
    unmount();

    renderPage({
      datasetInfoByJob: { "sch-1": { label: "public.archive", nature: "BATCH_TIME" } },
    });
    expect(screen.getByText("Toplu (Batch)")).toBeVisible();
  });
});
