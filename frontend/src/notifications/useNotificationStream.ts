import { useCallback, useEffect, useRef, useState } from "react";

/**
 * SSE event payload from the notification stream.
 */
export interface NotificationStreamEvent {
  type: string;
  data: Record<string, unknown>;
}

interface UseNotificationStreamOptions {
  /** Whether the stream should be active (typically true when user is logged in). */
  enabled: boolean;
  /** Called when a new_delivery event arrives. */
  onNewDelivery?: (payload: Record<string, unknown>) => void;
  /** Called when a mark_read event arrives. */
  onMarkRead?: (payload: Record<string, unknown>) => void;
}

interface UseNotificationStreamResult {
  /** Whether the SSE connection is currently open. */
  connected: boolean;
  /** Last error, if any. */
  lastError: string | null;
}

const INITIAL_BACKOFF_MS = 1_000;
const MAX_BACKOFF_MS = 30_000;

/**
 * Custom hook that maintains an SSE connection to the notification stream.
 *
 * Features:
 * - Automatic reconnect with exponential backoff
 * - Cleanup on unmount
 * - Event dispatching via callbacks
 */
export function useNotificationStream(
  options: UseNotificationStreamOptions,
): UseNotificationStreamResult {
  const { enabled, onNewDelivery, onMarkRead } = options;
  const [connected, setConnected] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const backoffRef = useRef(INITIAL_BACKOFF_MS);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);

  // Keep callbacks in refs so the effect doesn't re-run on every render
  const onNewDeliveryRef = useRef(onNewDelivery);
  const onMarkReadRef = useRef(onMarkRead);
  onNewDeliveryRef.current = onNewDelivery;
  onMarkReadRef.current = onMarkRead;

  const connect = useCallback(() => {
    if (unmountedRef.current) return;

    // Close existing connection if any
    eventSourceRef.current?.close();
    eventSourceRef.current = null;

    // EventSource cannot send custom headers; pass user ID as query parameter
    let userId = "";
    try {
      userId = localStorage.getItem("development-user-id") ?? "";
    } catch {
      // localStorage not available
    }
    const params = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
    const es = new EventSource(`/api/v1/notifications/stream${params}`);
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnected(true);
      setLastError(null);
      backoffRef.current = INITIAL_BACKOFF_MS;
    };

    es.addEventListener("new_delivery", (event: MessageEvent) => {
      try {
        const parsed = JSON.parse(event.data) as NotificationStreamEvent;
        onNewDeliveryRef.current?.(parsed.data ?? parsed);
      } catch {
        // Non-fatal: malformed event
      }
    });

    es.addEventListener("mark_read", (event: MessageEvent) => {
      try {
        const parsed = JSON.parse(event.data) as NotificationStreamEvent;
        onMarkReadRef.current?.(parsed.data ?? parsed);
      } catch {
        // Non-fatal: malformed event
      }
    });

    es.onerror = () => {
      setConnected(false);
      setLastError("SSE connection lost");
      es.close();
      eventSourceRef.current = null;

      // Schedule reconnect with exponential backoff
      const delay = Math.min(backoffRef.current, MAX_BACKOFF_MS);
      backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF_MS);
      reconnectTimerRef.current = setTimeout(() => {
        if (!unmountedRef.current) {
          connect();
        }
      }, delay);
    };
  }, []);

  useEffect(() => {
    unmountedRef.current = false;

    if (enabled) {
      connect();
    }

    return () => {
      unmountedRef.current = true;
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
      if (reconnectTimerRef.current !== null) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };
  }, [enabled, connect]);

  return { connected, lastError };
}
