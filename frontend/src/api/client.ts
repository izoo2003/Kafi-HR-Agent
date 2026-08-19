import { keysToCamel, keysToSnake } from "../lib/case";
import type { ApiErrorResponse } from "../types/common";

const RAW_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api/v1";
const PRODUCTION_API = "https://kafi-hr-agent.up.railway.app/api/v1";

/** Prefer absolute Railway URL in production builds; never call the Vercel origin for API. */
function resolveApiBase(): string {
  const configured = (RAW_BASE || "/api/v1").replace(/\/$/, "");
  if (configured.startsWith("http://") || configured.startsWith("https://")) {
    return configured;
  }
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host.endsWith("vercel.app") || host === "kafi-hr-agent.vercel.app") {
      return PRODUCTION_API;
    }
  }
  return configured;
}

const BASE_URL = resolveApiBase();

const ACCESS_KEY = "hr_access_token";
const REFRESH_KEY = "hr_refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export class ApiError extends Error {
  code: string;
  status: number;
  details?: Record<string, unknown> | null;

  constructor(status: number, body: ApiErrorResponse | string) {
    if (typeof body === "string") {
      super(body);
      this.code = "internal_error";
      this.details = null;
    } else {
      super(body.error.message);
      this.code = body.error.code;
      this.details = body.error.details;
    }
    this.status = status;
    this.name = "ApiError";
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
  auth?: boolean;
  formData?: FormData;
};

function buildUrl(path: string, params?: RequestOptions["params"]): string {
  const base = BASE_URL.replace(/\/$/, "");
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  // Absolute API host (Railway) or relative path (local Vite proxy).
  const url = new URL(`${base}${cleanPath}`, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) {
        const snakeKey = k.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`);
        url.searchParams.set(snakeKey, String(v));
      }
    }
  }
  // Keep full URL for absolute bases; path-only for relative (/api/v1).
  return base.startsWith("http://") || base.startsWith("https://")
    ? url.toString()
    : url.pathname + url.search;
}

let onUnauthorized: (() => void) | null = null;

export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const useAuth = options.auth !== false;
  if (useAuth) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let body: BodyInit | undefined;
  if (options.formData) {
    body = options.formData;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(keysToSnake(options.body));
  }

  const response = await fetch(buildUrl(path, options.params), {
    method: options.method ?? (options.body || options.formData ? "POST" : "GET"),
    headers,
    body,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  if (!response.ok) {
    const err =
      parsed && typeof parsed === "object" && "error" in (parsed as object)
        ? new ApiError(response.status, keysToCamel<ApiErrorResponse>(parsed))
        : new ApiError(
            response.status,
            typeof parsed === "string" && parsed.trim()
              ? parsed
              : `Request failed (${response.status})`,
          );
    if (err.code === "unauthorized" || response.status === 401) {
      onUnauthorized?.();
    }
    throw err;
  }

  return keysToCamel<T>(parsed);
}

function readApiErrorMessage(parsed: unknown, fallback: string): string {
  if (!parsed || typeof parsed !== "object") return fallback;
  const rec = parsed as Record<string, unknown>;
  const wrapped = rec.error as { message?: string } | undefined;
  if (typeof wrapped?.message === "string" && wrapped.message.trim()) {
    return wrapped.message.trim();
  }
  const detail = rec.detail;
  if (typeof detail === "string" && detail.trim()) return detail.trim();
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string };
    if (typeof first?.msg === "string" && first.msg.trim()) return first.msg.trim();
  }
  return fallback;
}

export async function fetchBlob(path: string, options: RequestOptions = {}): Promise<Blob> {
  const headers: Record<string, string> = {};
  const useAuth = options.auth !== false;
  if (useAuth) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let body: BodyInit | undefined;
  if (options.formData) {
    body = options.formData;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(keysToSnake(options.body));
  } else if ((options.method ?? "GET").toUpperCase() === "POST") {
    headers["Content-Type"] = "application/json";
    body = "{}";
  }

  const response = await fetch(buildUrl(path, options.params), {
    method: options.method ?? "GET",
    headers,
    body,
  });
  if (!response.ok) {
    if (response.status === 401) onUnauthorized?.();
    let message = `File download failed (${response.status})`;
    try {
      message = readApiErrorMessage(await response.json(), message);
    } catch {
      // keep generic message
    }
    throw new ApiError(response.status, message);
  }
  return response.blob();
}
