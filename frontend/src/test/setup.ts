import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => cleanup());

// jsdom does not provide EventSource; stub it so components that
// open SSE connections (e.g. NotificationBell) can mount safely.
if (typeof globalThis.EventSource === "undefined") {
  class EventSourceStub {
    static readonly CONNECTING = 0;
    static readonly OPEN = 1;
    static readonly CLOSED = 2;
    readonly CONNECTING = 0;
    readonly OPEN = 1;
    readonly CLOSED = 2;
    readyState = EventSourceStub.CONNECTING;
    url: string;
    onopen: ((ev: Event) => void) | null = null;
    onmessage: ((ev: MessageEvent) => void) | null = null;
    onerror: ((ev: Event) => void) | null = null;
    addEventListener() {}
    removeEventListener() {}
    close() { this.readyState = EventSourceStub.CLOSED; }
    dispatchEvent() { return false; }
    constructor(url: string) { this.url = url; }
  }
  (globalThis as Record<string, unknown>).EventSource = EventSourceStub;
}
