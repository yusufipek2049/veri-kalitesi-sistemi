import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { MemoryRouter } from "react-router-dom";
import { AppShell } from "./AppShell";
import { LauncherControlProvider } from "../launcherControl";

vi.mock("./NotificationBell", () => ({
  NotificationBell: () => <button aria-label="Bildirimler">Bildirimler</button>,
}));

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
  window.sessionStorage.clear();
  window.history.replaceState({}, "", "/");
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

const launcherSession = {
  port: 43_210,
  token: "launcher_control_token_0123456789_ABCDEFG",
};

function renderLauncherShell() {
  const encoded = btoa(JSON.stringify(launcherSession))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  window.history.replaceState({}, "", `/#vk-control=${encoded}`);
  return render(
    <ThemeModeProvider>
      <MemoryRouter>
        <LauncherControlProvider>
          <AppShell><p>İçerik</p></AppShell>
        </LauncherControlProvider>
      </MemoryRouter>
    </ThemeModeProvider>,
  );
}

describe("AppShell", () => {
  it("navigasyonu analiz ve operasyon gruplarında hizalı ikonlarla gösterir", () => {
    renderShell();

    expect(screen.getByRole("heading", { name: "ANALİZ" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "OPERASYON" })).toBeVisible();
    expect(screen.getAllByTestId("navigation-icon-slot")).toHaveLength(13);
    expect(screen.getByRole("link", { name: "Veri Kaynakları" })).toHaveAttribute("href", "/data-sources");
    expect(screen.getByRole("link", { name: "Katalog" })).toHaveAttribute("href", "/catalog");
    expect(screen.getByRole("link", { name: "Skorlar" })).toHaveAttribute("href", "/scores");
    expect(screen.getByRole("link", { name: "Skorlama Politikası" })).toHaveAttribute("href", "/scores/policy");
    expect(screen.getByRole("link", { name: "Kalite Analizleri" })).toHaveAttribute("href", "/analytics");
    expect(screen.getByRole("link", { name: "Yönetişim Görevleri" })).toHaveAttribute("href", "/governance");
    expect(screen.getByRole("link", { name: "Jobs" })).toHaveAttribute("href", "/jobs");
    expect(screen.getByRole("link", { name: "Bildirimler" })).toHaveAttribute("href", "/notifications");
    expect(screen.getByRole("link", { name: "Denetim" })).toHaveAttribute("href", "/audit");
    expect(screen.getByRole("link", { name: "Genel Bakış" })).toHaveAttribute("href", "/dashboard");
    expect(screen.queryByRole("link", { name: "Profiller" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Raporlar" })).not.toBeInTheDocument();
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

  it("launcher oturumu yoksa Kapat eylemini pasif gösterir", () => {
    renderShell();

    expect(screen.getByRole("button", { name: "Kapat" })).toBeDisabled();
  });

  it("onay dialog'unu erişilebilir açar ve Vazgeç POST göndermez", async () => {
    const fetchMock = vi.spyOn(window, "fetch");
    renderLauncherShell();

    fireEvent.click(screen.getByRole("button", { name: "Kapat" }));
    const dialog = screen.getByRole("dialog", { name: "Veri Kalitesi Sistemi kapatılsın mı?" });
    expect(dialog).toHaveAccessibleDescription(
      "Uygulama servisleri durdurulacak. Veritabanı verileri silinmeyecektir.",
    );
    await waitFor(() => expect(screen.getByRole("button", { name: "Uygulamayı kapat" })).toHaveFocus());

    fireEvent.click(screen.getByRole("button", { name: "Vazgeç" }));
    expect(fetchMock).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("onaydan sonra doğru endpoint/header ile yalnız tek POST gönderir", async () => {
    const fetchMock = vi.spyOn(window, "fetch").mockResolvedValue(new Response(null, { status: 202 }));
    const { container } = renderLauncherShell();

    fireEvent.click(screen.getByRole("button", { name: "Kapat" }));
    fireEvent.click(screen.getByRole("button", { name: "Uygulamayı kapat" }));

    expect(await screen.findByText("Uygulama kapatılıyor…")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:43210/v1/shutdown",
      {
        headers: { "X-Veri-Kalitesi-Control-Token": launcherSession.token },
        method: "POST",
      },
    );
    expect(container).not.toHaveTextContent(launcherSession.token);
  });

  it("reddedilen istekte teknik hata ve tekrar deneme sunar", async () => {
    const fetchMock = vi.spyOn(window, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 403 }))
      .mockResolvedValueOnce(new Response(null, { status: 202 }));
    const { container } = renderLauncherShell();

    fireEvent.click(screen.getByRole("button", { name: "Kapat" }));
    fireEvent.click(screen.getByRole("button", { name: "Uygulamayı kapat" }));
    expect(await screen.findByRole("dialog", { name: "Teknik hata" })).toBeVisible();
    expect(container).not.toHaveTextContent(launcherSession.token);

    fireEvent.click(screen.getByRole("button", { name: "Tekrar dene" }));
    expect(await screen.findByText("Uygulama kapatılıyor…")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
