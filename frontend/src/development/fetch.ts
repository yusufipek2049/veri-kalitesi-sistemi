/**
 * Geliştirme modu için API yardımcısı.
 *
 * İsteklere otomatik olarak:
 *  - X-Development-User-Id (localStorage'dan)
 *  - X-CSRF-Token (modül-düzeyinde tutulan, her yanıttan güncellenen kanıt)
 * ekler. CSRF kanıtı, GET/HEAD/OPTIONS dışı tüm isteklerde otomatik gönderilir;
 * her yanıttan X-CSRF-Token header'ı okunup depolanır.
 *
 * Domain modülleri CSRF yönetimiyle ilgilenmez — tüm kanıt akışı buradan yürütülür.
 */

const CSRF_HEADER = "X-CSRF-Token";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

let csrfProof: string | undefined;

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

export function stateChangingHeaders(): Record<string, string> {
  const headers = getDevelopmentHeaders();
  if (csrfProof) headers[CSRF_HEADER] = csrfProof;
  return headers;
}

export function recordCsrfProof(value: string | null): void {
  if (value) csrfProof = value;
}

export function developmentFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = {
    ...getDevelopmentHeaders(),
    ...(init?.headers as Record<string, string> ?? {}),
  };
  // Ensure Content-Type is preserved
  if (init?.body && typeof init.body === "string") {
    headers["Content-Type"] = headers["Content-Type"] ?? "application/json";
  }
  // Auto-attach CSRF proof for state-changing requests (unless caller already set it)
  if (!SAFE_METHODS.has(method) && csrfProof && !headers[CSRF_HEADER]) {
    headers[CSRF_HEADER] = csrfProof;
  }
  return fetch(input, { ...init, headers }).then(async (response) => {
    recordCsrfProof(response.headers.get(CSRF_HEADER));
    return response;
  });
}

/** @internal Testlerde CSRF durumunu sıfırlamak için — üretim kodunda kullanmayın. */
export function __resetCsrfProof(): void {
  csrfProof = undefined;
}
