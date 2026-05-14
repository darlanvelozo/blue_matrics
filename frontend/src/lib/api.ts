/**
 * Cliente HTTP do frontend. Lida com:
 *  - injeção do header Authorization
 *  - refresh automático em 401
 *  - parsing do envelope de erro { error: { code, message, details } } do backend
 */
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ACCESS_KEY = "bm.access";
const REFRESH_KEY = "bm.refresh";

export class ApiError extends Error {
  code: string;
  status: number;
  details: unknown;

  constructor(opts: { message: string; code: string; status: number; details?: unknown }) {
    super(opts.message);
    this.code = opts.code;
    this.status = opts.status;
    this.details = opts.details;
  }
}

export const tokens = {
  get access(): string | null {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(ACCESS_KEY);
  },
  get refresh(): string | null {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh: string) {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(ACCESS_KEY, access);
    window.localStorage.setItem(REFRESH_KEY, refresh);
  },
  setAccess(access: string) {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(ACCESS_KEY, access);
  },
  clear() {
    if (typeof window === "undefined") return;
    window.localStorage.removeItem(ACCESS_KEY);
    window.localStorage.removeItem(REFRESH_KEY);
  },
};

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokens.refresh;
  if (!refresh) return null;
  const res = await fetch(`${API_URL}/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) return null;
  const data = (await res.json()) as { access: string; refresh?: string };
  tokens.setAccess(data.access);
  if (data.refresh) {
    window.localStorage.setItem(REFRESH_KEY, data.refresh);
  }
  return data.access;
}

type FetchOptions = RequestInit & { skipAuth?: boolean; retried?: boolean };

export async function apiFetch<T = unknown>(path: string, opts: FetchOptions = {}): Promise<T> {
  const { skipAuth, retried, headers, ...rest } = opts;

  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(headers as Record<string, string>),
  };
  if (!skipAuth) {
    const access = tokens.access;
    if (access) finalHeaders.Authorization = `Bearer ${access}`;
  }

  const res = await fetch(`${API_URL}${path}`, { ...rest, headers: finalHeaders });

  if (res.status === 401 && !skipAuth && !retried) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiFetch<T>(path, { ...opts, retried: true });
    }
    tokens.clear();
  }

  let body: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!res.ok) {
    const err =
      body && typeof body === "object" && "error" in (body as Record<string, unknown>)
        ? ((body as Record<string, unknown>).error as Record<string, unknown>)
        : null;
    throw new ApiError({
      message: (err?.message as string) ?? `HTTP ${res.status}`,
      code: (err?.code as string) ?? "http_error",
      status: res.status,
      details: err?.details,
    });
  }

  return body as T;
}
