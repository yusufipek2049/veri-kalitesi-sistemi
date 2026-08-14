import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

const STORAGE_KEY = "veri-kalitesi-launcher-control";
const FRAGMENT_PREFIX = "#vk-control=";
const TOKEN_HEADER = "X-Veri-Kalitesi-Control-Token";

export interface LauncherControlSession {
  port: number;
  token: string;
}

export type LauncherShutdownStatus = "idle" | "requesting" | "closing" | "closed" | "error";

interface LauncherControlValue {
  available: boolean;
  cancelError: () => void;
  requestShutdown: () => Promise<void>;
  status: LauncherShutdownStatus;
}

const LauncherControlContext = createContext<LauncherControlValue>({
  available: false,
  cancelError: () => undefined,
  requestShutdown: async () => undefined,
  status: "idle",
});

function isSession(value: unknown): value is LauncherControlSession {
  if (!value || typeof value !== "object" || Object.keys(value).length !== 2) return false;
  const candidate = value as Partial<LauncherControlSession>;
  return (
    Number.isInteger(candidate.port) &&
    Number(candidate.port) >= 1 &&
    Number(candidate.port) <= 65_535 &&
    typeof candidate.token === "string" &&
    candidate.token.length >= 32 &&
    candidate.token.length <= 128 &&
    /^[A-Za-z0-9_-]+$/.test(candidate.token)
  );
}

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padding = "=".repeat((4 - (normalized.length % 4)) % 4);
  return atob(normalized + padding);
}

function parseSession(value: string): LauncherControlSession | null {
  try {
    const parsed: unknown = JSON.parse(value);
    return isSession(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function consumeLauncherControlSession(): LauncherControlSession | null {
  let fragmentSession: LauncherControlSession | null = null;
  if (window.location.hash.startsWith(FRAGMENT_PREFIX)) {
    const encoded = window.location.hash.slice(FRAGMENT_PREFIX.length);
    try {
      fragmentSession = parseSession(decodeBase64Url(decodeURIComponent(encoded)));
    } catch {
      fragmentSession = null;
    }
    window.history.replaceState(
      window.history.state,
      "",
      `${window.location.pathname}${window.location.search}`,
    );
    if (fragmentSession) {
      try {
        window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(fragmentSession));
      } catch {
        // Bellekteki oturum kullanılabilir; kalıcı depoya geri düşülmez.
      }
      return fragmentSession;
    }
  }

  try {
    const stored = window.sessionStorage.getItem(STORAGE_KEY);
    if (!stored) return null;
    const session = parseSession(stored);
    if (!session) window.sessionStorage.removeItem(STORAGE_KEY);
    return session;
  } catch {
    return null;
  }
}

export function LauncherControlProvider({ children }: { children: ReactNode }) {
  const [session] = useState<LauncherControlSession | null>(consumeLauncherControlSession);
  const [status, setStatus] = useState<LauncherShutdownStatus>("idle");
  const requestInFlight = useRef(false);
  const closingTimers = useRef<number[]>([]);

  useEffect(() => () => {
    closingTimers.current.forEach((timer) => window.clearTimeout(timer));
  }, []);

  const requestShutdown = useCallback(async () => {
    if (!session || requestInFlight.current) return;
    requestInFlight.current = true;
    setStatus("requesting");
    try {
      const response = await fetch(`http://127.0.0.1:${session.port}/v1/shutdown`, {
        headers: { [TOKEN_HEADER]: session.token },
        method: "POST",
      });
      if (response.status !== 202) throw new Error("shutdown rejected");
      try {
        window.sessionStorage.removeItem(STORAGE_KEY);
      } catch {
        // Oturum zaten yalnız bellekte tutuluyor olabilir.
      }
      setStatus("closing");
      const closedTimer = window.setTimeout(() => {
        setStatus("closed");
        const windowCloseTimer = window.setTimeout(() => {
          try {
            window.close();
          } catch {
            // Tarayıcı güvenlik modeli programatik sekme kapatmayı reddedebilir.
          }
        }, 250);
        closingTimers.current.push(windowCloseTimer);
      }, 1_500);
      closingTimers.current.push(closedTimer);
    } catch {
      requestInFlight.current = false;
      setStatus("error");
    }
  }, [session]);

  const cancelError = useCallback(() => {
    requestInFlight.current = false;
    setStatus("idle");
  }, []);

  const value = useMemo<LauncherControlValue>(
    () => ({ available: session !== null, cancelError, requestShutdown, status }),
    [cancelError, requestShutdown, session, status],
  );

  return (
    <LauncherControlContext.Provider value={value}>
      {children}
    </LauncherControlContext.Provider>
  );
}

export function useLauncherControl(): LauncherControlValue {
  return useContext(LauncherControlContext);
}
