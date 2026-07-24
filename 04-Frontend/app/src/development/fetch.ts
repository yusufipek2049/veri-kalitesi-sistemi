/** Geliştirme modu için API yardımcısı — isteklere X-Development-User-Id header'ını ekler. */

export function getDevelopmentHeaders(): Record<string, string> {
  try {
    const userId = localStorage.getItem("development-user-id");
    if (userId) {
      return { "X-Development-User-Id": userId };
    }
  } catch {
    // localStorage not available
  }
  return {};
}

export function developmentFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const headers: Record<string, string> = {
    ...getDevelopmentHeaders(),
    ...(init?.headers as Record<string, string> ?? {}),
  };
  // Ensure Content-Type is preserved
  if (init?.body && typeof init.body === "string") {
    headers["Content-Type"] = headers["Content-Type"] ?? "application/json";
  }
  return fetch(input, { ...init, headers });
}