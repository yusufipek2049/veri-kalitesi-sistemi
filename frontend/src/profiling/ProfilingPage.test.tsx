import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { ProfilingPage } from "./ProfilingPage";
import {
  syntheticDriftJudgment,
  syntheticSnapshotDetail,
  syntheticSnapshots,
  type DriftJudgment,
  type ProfileSnapshotDetail,
} from "./model";

function renderPage(props: Partial<React.ComponentProps<typeof ProfilingPage>> = {}) {
  return render(
    <ThemeModeProvider>
      <MemoryRouter initialEntries={["/profiling"]}>
        <ProfilingPage {...props} />
      </MemoryRouter>
    </ThemeModeProvider>,
  );
}

describe("ProfilingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders snapshot list", () => {
    renderPage({ state: "normal", snapshots: syntheticSnapshots });
    expect(screen.getByText("profile-001")).toBeInTheDocument();
    expect(screen.getByText("profile-002")).toBeInTheDocument();
  });

  it("shows loading state", () => {
    renderPage({ state: "loading" });
    expect(screen.getByText(/Profil Snapshotları/i)).toBeInTheDocument();
  });

  it("shows empty state", () => {
    renderPage({ state: "empty", snapshots: [] });
    expect(screen.getByText(/profil snapshot bulunamadı/i)).toBeInTheDocument();
  });

  it("shows unauthorized state", () => {
    renderPage({ state: "unauthorized" });
    expect(screen.getByText(/yetkiniz yok/i)).toBeInTheDocument();
  });

  it("shows error state with correlation ID", () => {
    renderPage({ state: "error", correlationId: "corr-123" });
    expect(screen.getByText(/corr-123/i)).toBeInTheDocument();
  });

  it("renders selected snapshot detail", () => {
    renderPage({
      state: "normal",
      snapshots: syntheticSnapshots,
      selectedSnapshot: syntheticSnapshotDetail,
    });
    expect(screen.getByText(/Snapshot Detayı/i)).toBeInTheDocument();
    expect(screen.getByText("profile-001")).toBeInTheDocument();
  });

  it("shows masked fields in metrics", () => {
    const maskedDetail: ProfileSnapshotDetail = {
      ...syntheticSnapshotDetail,
      metrics: {
        row_count: 1000,
        masked_field: "***MASKED***",
        profile_contract: {
          snapshot_version: "DQ_PROFILE_SNAPSHOT_V1",
          policy_version: "POLICY_V1",
          fingerprint: "abc123",
        },
      },
    };
    renderPage({
      state: "normal",
      snapshots: syntheticSnapshots,
      selectedSnapshot: maskedDetail,
    });
    expect(screen.getByText(/\*\*\*MASKED\*\*\*/i)).toBeInTheDocument();
  });

  it("shows Unknown judgment for INSUFFICIENT_HISTORY", () => {
    const unknownJudgment: DriftJudgment = {
      ...syntheticDriftJudgment,
      status: "INSUFFICIENT_HISTORY",
      message: "No baseline available",
    };
    renderPage({
      state: "normal",
      snapshots: syntheticSnapshots,
      driftJudgment: unknownJudgment,
    });
    expect(screen.getByText(/No baseline available/i)).toBeInTheDocument();
    expect(screen.getByText(/drift hükmü üretilemedi/i)).toBeInTheDocument();
  });

  it("shows Unknown judgment for CONFIGURATION_ERROR", () => {
    const configErrorJudgment: DriftJudgment = {
      ...syntheticDriftJudgment,
      status: "CONFIGURATION_ERROR",
      result: { configuration_error: "ACTIVE_PROFILE_POLICY_MISSING" },
      message: "Policy missing",
    };
    renderPage({
      state: "normal",
      snapshots: syntheticSnapshots,
      driftJudgment: configErrorJudgment,
    });
    expect(screen.getByText(/ACTIVE_PROFILE_POLICY_MISSING/i)).toBeInTheDocument();
  });

  it("shows drift signals table for COMPLETED judgment", () => {
    renderPage({
      state: "normal",
      snapshots: syntheticSnapshots,
      driftJudgment: syntheticDriftJudgment,
    });
    expect(screen.getByText(/Drift Hükmü/i)).toBeInTheDocument();
    expect(screen.getByText("VOLUME_CHANGE")).toBeInTheDocument();
  });

  it("shows bounded result indicator", () => {
    renderPage({
      state: "normal",
      snapshots: syntheticSnapshots,
      limit: 50,
    });
    expect(screen.getByText(/Gösterilen: 2 \/ 50/i)).toBeInTheDocument();
  });

  it("shows invalid profile ID warning", () => {
    render(
      <ThemeModeProvider>
        <MemoryRouter initialEntries={["/profiling?profile_id="]}>
          <ProfilingPage state="normal" snapshots={syntheticSnapshots} />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    expect(screen.getByText(/Geçersiz profil kimliği/i)).toBeInTheDocument();
  });

  it("calls onSelectSnapshot when row is clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    renderPage({
      state: "normal",
      snapshots: syntheticSnapshots,
      onSelectSnapshot: onSelect,
    });
    const row = screen.getByLabelText(/Snapshot profile-001 seç/i);
    await user.click(row);
    expect(onSelect).toHaveBeenCalledWith("profile-001");
  });

  it("supports keyboard navigation on rows", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    renderPage({
      state: "normal",
      snapshots: syntheticSnapshots,
      onSelectSnapshot: onSelect,
    });
    const row = screen.getByLabelText(/Snapshot profile-001 seç/i);
    row.focus();
    await user.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledWith("profile-001");
  });

  it("shows policy version in drift judgment", () => {
    renderPage({
      state: "normal",
      snapshots: syntheticSnapshots,
      driftJudgment: syntheticDriftJudgment,
    });
    expect(screen.getByText(/Politika: POLICY_V1/i)).toBeInTheDocument();
  });

  it("distinguishes no data from unauthorized from unknown judgment", () => {
    const { rerender } = renderPage({ state: "empty", snapshots: [] });
    expect(screen.getByText(/profil snapshot bulunamadı/i)).toBeInTheDocument();

    rerender(
      <ThemeModeProvider>
        <MemoryRouter initialEntries={["/profiling"]}>
          <ProfilingPage state="unauthorized" />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    expect(screen.getByText(/yetkiniz yok/i)).toBeInTheDocument();

    const unknownJudgment: DriftJudgment = {
      ...syntheticDriftJudgment,
      status: "INSUFFICIENT_HISTORY",
      message: "No baseline available for this snapshot",
    };
    rerender(
      <ThemeModeProvider>
        <MemoryRouter initialEntries={["/profiling"]}>
          <ProfilingPage
            state="normal"
            snapshots={syntheticSnapshots}
            driftJudgment={unknownJudgment}
          />
        </MemoryRouter>
      </ThemeModeProvider>,
    );
    expect(screen.getByText(/No baseline available/i)).toBeInTheDocument();
  });
});
