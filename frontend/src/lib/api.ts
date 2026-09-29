import { z } from "zod";
import { ApiError, ApiErrorBody } from "./types";

const API_BASE = "";  // use relative URLs so Next.js proxies /api/* to the backend

/**
 * Typed fetch wrapper with credentials: 'include' (cookie-only auth).
 * Never logs or stores tokens — constitution: cookie only.
 */
export async function apiFetch<T>(
  path: string,
  schema: z.ZodType<T>,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Unknown error" }));
    const parsed = ApiErrorBody.safeParse(body);
    throw new ApiError(
      res.status,
      parsed.success ? parsed.data : { detail: "Unknown error" }
    );
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const json = await res.json();
  const result = schema.safeParse(json);
  if (!result.success) {
    throw new ApiError(422, {
      detail: `Response validation failed: ${result.error.message}`,
    });
  }
  return result.data;
}

/**
 * Fetch without Zod parsing (for HTML responses, text, etc.)
 */
export async function apiFetchRaw(
  path: string,
  options?: RequestInit
): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...options,
  });
}
