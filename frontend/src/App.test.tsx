import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ThemeModeProvider } from "./theme/ThemeModeProvider";

vi.mock("./components/AppShell", () => ({
  AppShell: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("./dataSources/DataSourcesRoute", () => ({
  DataSourcesRoute: () => <div>Veri kaynakları rotası</div>,
}));
vi.mock("./dashboard/DashboardPage", () => ({
  DashboardPage: () => <div>Genel Bakış rotası</div>,
}));

import { ApplicationRoutes } from "./App";

function renderRoute(path: string) {
  return render(
    <ThemeModeProvider>
      <MemoryRouter initialEntries={[path]}><ApplicationRoutes /></MemoryRouter>
    </ThemeModeProvider>,
  );
}

describe("production route surface", () => {
  it("ana rotayı genel bakış yüzeyine yönlendirir", async () => {
    renderRoute("/");

    expect(await screen.findByText("Genel Bakış rotası")).toBeInTheDocument();
  });

  it.each(["/profiling", "/reports", "/investigation"])(
    "%s phantom sayfasına yönlenmeye izin vermez",
    (path) => {
      renderRoute(path);

      expect(screen.getByText("Sayfa bulunamadı")).toBeInTheDocument();
    },
  );
});
