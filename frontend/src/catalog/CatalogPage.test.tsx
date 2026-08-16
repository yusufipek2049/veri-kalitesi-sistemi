import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { CatalogPage } from "./CatalogPage";
import type { CatalogDataset } from "./model";

function renderPage(props: Parameters<typeof CatalogPage>[0] = {}) {
  return render(
    <ThemeModeProvider>
      <MemoryRouter>
        <CatalogPage {...props} />
      </MemoryRouter>
    </ThemeModeProvider>,
  );
}

const sampleDatasets: CatalogDataset[] = [
  {
    id: "ds-1",
    dataSourceId: "source-1",
    namespace: "public",
    name: "accounts",
    datasetType: "TABLE",
    status: "ACTIVE",
    estimatedRowCount: 1000,
    fieldCount: 5,
    version: 1,
    ownerId: null,
  },
  {
    id: "ds-2",
    dataSourceId: "source-1",
    namespace: "public",
    name: "transactions",
    datasetType: "TABLE",
    status: "INACTIVE",
    estimatedRowCount: null,
    fieldCount: 12,
    version: 2,
    ownerId: "user-owner",
  },
];

describe("CatalogPage", () => {
  it("renders dataset list in normal state", () => {
    renderPage({ state: "normal", items: sampleDatasets });
    expect(screen.getByText("accounts")).toBeVisible();
    expect(screen.getByText("transactions")).toBeVisible();
    expect(screen.getByText("2 dataset")).toBeVisible();
  });

  it("renders loading skeletons", () => {
    renderPage({ state: "loading" });
    expect(screen.getByLabelText("Katalog yükleniyor")).toBeVisible();
  });

  it("renders empty state when no datasets", () => {
    renderPage({ state: "normal", items: [] });
    expect(screen.getByText("Katalog dataset bulunamadı")).toBeVisible();
  });

  it("renders error state with correlation id", () => {
    renderPage({ state: "error", correlationId: "corr-123" });
    expect(screen.getByText(/corr-123/)).toBeVisible();
  });

  it("renders unauthorized state", () => {
    renderPage({ state: "unauthorized" });
    expect(screen.getByText("Bu görünüm için yetkiniz yok")).toBeVisible();
  });

  it("filters datasets by name", () => {
    renderPage({ state: "normal", items: sampleDatasets });
    const searchInput = screen.getByRole("textbox", { name: /dataset ara/i });
    fireEvent.change(searchInput, { target: { value: "accounts" } });
    expect(screen.getByText("1 dataset")).toBeVisible();
  });

  it("shows page heading and description", () => {
    renderPage({ state: "normal", items: sampleDatasets });
    expect(screen.getByRole("heading", { name: "Katalog" })).toBeVisible();
    expect(screen.getByText("Keşfedilmiş dataset ve alan envanteri")).toBeVisible();
  });

  it("shows field count for each dataset", () => {
    renderPage({ state: "normal", items: sampleDatasets });
    expect(screen.getByText("5 alan")).toBeVisible();
    expect(screen.getByText("12 alan")).toBeVisible();
  });
});
