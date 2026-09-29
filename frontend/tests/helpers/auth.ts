import fs from "fs";
import path from "path";
import { request as playwrightRequest } from "@playwright/test";

const AUTH_STATE = path.join(__dirname, "..", "fixtures", "e2e-auth-state.json");

export function authStatePath(): string {
  return AUTH_STATE;
}

/**
 * Register once per hour-ish and reuse the cookie file afterwards, so E2E runs
 * stay within the backend's auth rate limit (20 requests / 5 minutes).
 */
export async function ensureSharedAuthState(baseURL: string): Promise<void> {
  if (fs.existsSync(AUTH_STATE)) {
    try {
      const state = JSON.parse(fs.readFileSync(AUTH_STATE, "utf8"));
      const cookie = (state.cookies ?? []).find(
        (c: { name: string }) => c.name === "access_token"
      );
      if (cookie && (cookie.expires ?? 0) * 1000 > Date.now() + 60_000) {
        return;
      }
    } catch {
      // unreadable state — fall through and register again
    }
  }

  const api = await playwrightRequest.newContext({
    baseURL,
    storageState: { cookies: [], origins: [] },
  });
  try {
    const res = await api.post("/api/v1/auth/register", {
      data: {
        email: `e2e-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
        password: "testpassword123",
      },
    });
    if (!res.ok()) {
      throw new Error(`register failed: ${res.status()} ${await res.text()}`);
    }
    await api.storageState({ path: AUTH_STATE });
  } finally {
    await api.dispose();
  }
}
