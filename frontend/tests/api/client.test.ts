import { afterEach, describe, expect, it, vi } from "vitest";

import { apiRequest } from "../../src/api/client";
import { ApiError } from "../../src/api/errors";
import {
  clearSessionToken,
  getSessionToken,
  setSessionToken,
} from "../../src/features/auth/session";

describe("apiRequest", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("unwraps data and sends bearer token", async () => {
    setSessionToken("token-123");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: { id: "course_1", name: "Calculus" },
          meta: { request_id: "req_1" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const data = await apiRequest<{ id: string; name: string }>("/api/v1/courses");

    expect(data).toEqual({ id: "course_1", name: "Calculus" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/courses",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token-123",
        }),
      }),
    );
  });

  it("normalizes api errors and clears token on unauthorized", async () => {
    setSessionToken("expired-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "UNAUTHORIZED",
              message: "登录已过期",
              details: { reason: "expired" },
            },
            meta: { request_id: "req_expired" },
          }),
          { status: 401, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    await expect(apiRequest("/api/v1/auth/me")).rejects.toMatchObject({
      code: "UNAUTHORIZED",
      message: "登录已过期",
      details: { reason: "expired" },
      status: 401,
    });
    expect(getSessionToken()).toBeNull();
  });

  it("serializes plain object bodies as json", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: { ok: true }, meta: {} }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/api/v1/auth/login", {
      method: "POST",
      body: { username: "student@example.com", password: "password123" },
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/login",
      expect.objectContaining({
        body: JSON.stringify({
          username: "student@example.com",
          password: "password123",
        }),
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      }),
    );
  });

  it("does not send authorization after token is cleared", async () => {
    setSessionToken("token-123");
    clearSessionToken();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: null, meta: {} }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/api/v1/auth/logout", { method: "POST" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/logout",
      expect.objectContaining({
        headers: expect.not.objectContaining({
          Authorization: expect.any(String),
        }),
      }),
    );
  });

  it.each([
    "https://attacker.example/api/v1/courses",
    "//attacker.example/api/v1/courses",
    "/api/v1/../outside",
    "/api/v1/courses#token",
  ])("rejects an untrusted target before sending credentials: %s", async (path) => {
    setSessionToken("sensitive-token");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest(path)).rejects.toThrow(/鉴权 API 请求/);

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
