import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiFetch, apiFetchRaw } from "@/lib/api";
import { ApiError } from "@/lib/types";
import { getErrorMessage, shouldRedirectToLogin, getRetryAfterMessage } from "@/lib/errors";

describe("apiFetch", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed data on 200", async () => {
    const data = { id: "1", name: "test" };
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve(data),
    });

    const schema = { safeParse: (d: any) => ({ success: true, data: d }) } as any;
    const result = await apiFetch("/test", schema);

    expect(result).toEqual(data);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/test"),
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("returns undefined on 204", async () => {
    fetchMock.mockResolvedValueOnce({ ok: true, status: 204 });

    const schema = { safeParse: (d: any) => ({ success: true, data: d }) } as any;
    const result = await apiFetch("/test", schema);

    expect(result).toBeUndefined();
  });

  it("throws ApiError on 401", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Not authenticated" }),
    });

    const schema = { safeParse: (d: any) => ({ success: true, data: d }) } as any;

    await expect(apiFetch("/test", schema)).rejects.toThrow(ApiError);
    await expect(apiFetch("/test", schema)).rejects.toMatchObject({
      status: 401,
    });
  });

  it("throws ApiError on 409 with detail", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: () => Promise.resolve({ detail: "Already exists" }),
    });

    const schema = { safeParse: (d: any) => ({ success: true, data: d }) } as any;

    await expect(apiFetch("/test", schema)).rejects.toMatchObject({
      status: 409,
      body: { detail: "Already exists" },
    });
  });

  it("throws ApiError on 422 with detail", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: () => Promise.resolve({ detail: "Validation error" }),
    });

    const schema = { safeParse: (d: any) => ({ success: true, data: d }) } as any;

    await expect(apiFetch("/test", schema)).rejects.toMatchObject({
      status: 422,
    });
  });

  it("throws ApiError on 500 with generic detail", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error("bad json")),
    });

    const schema = { safeParse: (d: any) => ({ success: true, data: d }) } as any;

    await expect(apiFetch("/test", schema)).rejects.toMatchObject({
      status: 500,
      body: { detail: "Unknown error" },
    });
  });

  it("throws ApiError on schema validation failure", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ invalid: true }),
    });

    const schema = {
      safeParse: () => ({ success: false, error: { message: "Invalid" } }),
    } as any;

    await expect(apiFetch("/test", schema)).rejects.toMatchObject({
      status: 422,
    });
  });

  it("includes Content-Type header", async () => {
    fetchMock.mockResolvedValueOnce({ ok: true, status: 204 });

    const schema = { safeParse: (d: any) => ({ success: true, data: d }) } as any;
    await apiFetch("/test", schema, { method: "POST" });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      })
    );
  });
});

describe("apiFetchRaw", () => {
  it("returns raw Response", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, status: 200 });
    vi.stubGlobal("fetch", fetchMock);

    const res = await apiFetchRaw("/test");
    expect(res.status).toBe(200);
    vi.unstubAllGlobals();
  });

  it("includes credentials: include", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, status: 200 });
    vi.stubGlobal("fetch", fetchMock);

    await apiFetchRaw("/test");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ credentials: "include" })
    );
    vi.unstubAllGlobals();
  });
});

describe("getErrorMessage", () => {
  it("returns 401 message", () => {
    expect(getErrorMessage(401)).toBe("Session expired — please sign in again");
  });

  it("returns 403 message", () => {
    expect(getErrorMessage(403)).toBe("You don't have access to this resource");
  });

  it("returns 404 message", () => {
    expect(getErrorMessage(404)).toBe("Resource not found");
  });

  it("returns 409 with detail", () => {
    expect(getErrorMessage(409, "Already exists")).toBe("Already exists");
  });

  it("returns 409 without detail", () => {
    expect(getErrorMessage(409)).toBe("This item already exists");
  });

  it("returns 422 with detail", () => {
    expect(getErrorMessage(422, "Check input")).toBe("Check input");
  });

  it("returns 500 generic message", () => {
    expect(getErrorMessage(500)).toBe("Something went wrong. Please try again.");
  });

  it("returns 502 generic message", () => {
    expect(getErrorMessage(502)).toBe("Something went wrong. Please try again.");
  });

  it("returns detail for unknown status", () => {
    expect(getErrorMessage(418, "Teapot")).toBe("Teapot");
  });

  it("returns generic for unknown status without detail", () => {
    expect(getErrorMessage(418)).toBe("Something went wrong. Please try again.");
  });
});

describe("shouldRedirectToLogin", () => {
  it("returns true for 401", () => {
    expect(shouldRedirectToLogin(401)).toBe(true);
  });

  it("returns false for 403", () => {
    expect(shouldRedirectToLogin(403)).toBe(false);
  });

  it("returns false for 404", () => {
    expect(shouldRedirectToLogin(404)).toBe(false);
  });
});

describe("getRetryAfterMessage", () => {
  it("returns default without retry-after", () => {
    expect(getRetryAfterMessage()).toBe("Rate limited — please try again later");
  });

  it("returns seconds message", () => {
    expect(getRetryAfterMessage("30")).toBe("Rate limited — try again in 30 seconds");
  });

  it("returns minutes message", () => {
    expect(getRetryAfterMessage("120")).toBe("Rate limited — try again in 2 minutes");
  });

  it("handles invalid retry-after", () => {
    expect(getRetryAfterMessage("abc")).toBe("Rate limited — please try again later");
  });
});
