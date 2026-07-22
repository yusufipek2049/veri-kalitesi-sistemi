import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { MemoryRouter } from "react-router-dom";
import { AppShell } from "./AppShell";

afterEach(() => {
  window.localStorage.clear();
  delete document.documentElement.dataset.theme;
});

function renderShell() {
  return render(
    <ThemeModeProvider>
      <MemoryRouter>
        <AppShell>
          <p>İçerik</p>
        </AppShell>
      </MemoryRouter>
    </ThemeModeProvider>,
  );
}

describe("AppShell", () => {
  it("navigasyonu analiz ve operasyon gruplarında hizalı ikonlarla gösterir", () => {
    renderShell();

    expect(screen.getByRole("heading", { name: "ANALİZ" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "OPERASYON" })).toBeVisible();
    expect(screen.getAllByTestId("navigation-icon-slot")).toHaveLength(7);
    expect(screen.getByRole("link", { name: "Veri Kaynakları" })).toHaveAttribute("href", "/data-sources");
    expect(screen.getByRole("link", { name: "Denetim" })).toHaveAttribute("href", "/audit");
  });

  it("açık temayla başlar ve koyu tema tercihini kalıcılaştırır", async () => {
    renderShell();

    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("light"));
    fireEvent.click(screen.getByRole("button", { name: "Koyu temaya geç" }));

    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("dark"));
    expect(window.localStorage.getItem("veri-kalitesi-theme")).toBe("dark");
    expect(screen.getByRole("button", { name: "Açık temaya geç" })).toBeVisible();
  });

  it("saklanan koyu tema tercihini ilk renderda uygular", async () => {
    window.localStorage.setItem("veri-kalitesi-theme", "dark");
    renderShell();

    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("dark"));
    expect(screen.getByRole("button", { name: "Açık temaya geç" })).toBeVisible();
  });

  it("tema tercihi okunamazsa açık temayla güvenli biçimde çalışır", async () => {
    const getItem = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("storage unavailable");
    });

    renderShell();

    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("light"));
    getItem.mockRestore();
  });

  it("tema tercihi yazılamasa da oturum içindeki seçimi uygular", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("storage unavailable");
    });
    renderShell();

    fireEvent.click(screen.getByRole("button", { name: "Koyu temaya geç" }));

    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("dark"));
    expect(screen.getByRole("button", { name: "Açık temaya geç" })).toBeVisible();
    setItem.mockRestore();
  });
});
