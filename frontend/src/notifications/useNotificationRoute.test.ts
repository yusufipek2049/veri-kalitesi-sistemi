import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { useNotificationRoute } from "./useNotificationRoute";

afterEach(() => {
  window.history.replaceState({}, "", "/");
});

it("does not call the loader when a notification fixture state is active", () => {
  window.history.replaceState({}, "", "/notifications?state=error");
  const loader = vi.fn(async () => ({ data: ["unexpected"], isEmpty: false }));

  const { result } = renderHook(() => useNotificationRoute<string[]>([], loader));

  expect(loader).not.toHaveBeenCalled();
  expect(result.current.state).toBe("error");
  expect(result.current.data).toEqual([]);
});

it("does not update state when an aborted load settles", async () => {
  let resolveAbortedLoad!: (value: { data: string[]; isEmpty: boolean }) => void;
  const abortedLoader = vi.fn(() => new Promise<{ data: string[]; isEmpty: boolean }>((resolve) => {
    resolveAbortedLoad = resolve;
  }));
  const currentLoader = vi.fn(async () => ({ data: ["current"], isEmpty: false }));
  const { rerender, result } = renderHook(
    ({ loader }) => useNotificationRoute<string[]>([], loader),
    { initialProps: { loader: abortedLoader } },
  );

  rerender({ loader: currentLoader });
  await waitFor(() => expect(result.current.state).toBe("normal"));

  await act(async () => {
    resolveAbortedLoad({ data: [], isEmpty: true });
    await Promise.resolve();
  });

  expect(result.current.state).toBe("normal");
  expect(result.current.data).toEqual(["current"]);
});
