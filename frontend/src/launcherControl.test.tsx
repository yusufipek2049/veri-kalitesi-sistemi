import { act, render, screen } from "@testing-library/react";
import { useLauncherControl, LauncherControlProvider, consumeLauncherControlSession } from "./launcherControl";
import { afterEach, describe, expect, it, vi } from "vitest";

const session = {
  port: 43_210,
  token: "launcher_control_token_0123456789_ABCDEFG",
};

function encodedSession(): string {
  return btoa(JSON.stringify(session)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  window.sessionStorage.clear();
  window.history.replaceState({}, "", "/");
});

describe("launcher control session", () => {
  it("fragment'i okur, sessionStorage'a taşır ve URL'den hemen temizler", () => {
    window.history.replaceState({}, "", `/#vk-control=${encodedSession()}`);

    expect(consumeLauncherControlSession()).toEqual(session);
    expect(window.location.hash).toBe("");
    expect(JSON.parse(window.sessionStorage.getItem("veri-kalitesi-launcher-control") ?? "null")).toEqual(session);
    expect(window.localStorage).toHaveLength(0);
  });

  it("geçersiz launcher fragment'ini temizler ve oturum oluşturmaz", () => {
    window.history.replaceState({}, "", "/#vk-control=not-valid-base64");

    expect(consumeLauncherControlSession()).toBeNull();
    expect(window.location.hash).toBe("");
    expect(window.sessionStorage).toHaveLength(0);
  });

  it("202 sonrasında kapanıyor ve ardından kapatıldı durumunu üretir", async () => {
    vi.useFakeTimers();
    window.history.replaceState({}, "", `/#vk-control=${encodedSession()}`);
    const fetchMock = vi.spyOn(window, "fetch").mockResolvedValue(new Response(null, { status: 202 }));

    function Probe() {
      const control = useLauncherControl();
      return (
        <div>
          <span>{control.status}</span>
          <button onClick={() => void control.requestShutdown()}>Gönder</button>
        </div>
      );
    }

    render(<LauncherControlProvider><Probe /></LauncherControlProvider>);
    screen.getByRole("button", { name: "Gönder" }).click();
    await act(async () => Promise.resolve());

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:43210/v1/shutdown",
      {
        headers: { "X-Veri-Kalitesi-Control-Token": session.token },
        method: "POST",
      },
    );
    expect(screen.getByText("closing")).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(1_500));
    expect(screen.getByText("closed")).toBeInTheDocument();
  });
});
