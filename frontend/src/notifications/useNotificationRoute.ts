import { useCallback, useEffect, useState } from "react";

export type NotificationRouteState =
  | "normal"
  | "loading"
  | "empty"
  | "error"
  | "unauthorized";

interface NotificationLoadResult<T> {
  data: T;
  isEmpty: boolean;
}

const notificationRouteStates: NotificationRouteState[] = [
  "normal",
  "loading",
  "empty",
  "error",
  "unauthorized",
];

export function useNotificationRoute<T>(
  initialData: T,
  loader: () => Promise<NotificationLoadResult<T>>,
) {
  const requestedState = new URLSearchParams(window.location.search).get("state") as NotificationRouteState | null;
  const fixtureState = import.meta.env.DEV
    && requestedState
    && notificationRouteStates.includes(requestedState)
    ? requestedState
    : null;
  const [state, setState] = useState<NotificationRouteState>(fixtureState ?? "loading");
  const [data, setData] = useState<T>(initialData);

  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const result = await loader();
      if (signal?.aborted) return;
      setData(result.data);
      setState(result.isEmpty ? "empty" : "normal");
    } catch {
      if (signal?.aborted) return;
      setState("error");
    }
  }, [fixtureState, loader]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  return {
    data,
    load,
    setData,
    state: fixtureState ?? state,
  };
}
