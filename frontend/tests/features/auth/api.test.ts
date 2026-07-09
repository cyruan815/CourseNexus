import { afterEach, describe, expect, it, vi } from "vitest";

import { login, register } from "../../../src/features/auth/api";
import { getSessionToken } from "../../../src/features/auth/session";

function authResponse(token: string) {
  return new Response(
    JSON.stringify({
      data: {
        access_token: token,
        token_type: "bearer",
        expires_at: "2026-07-10T12:00:00+00:00",
        user: {
          id: "usr_123",
          username: "student@example.com",
          nickname: "学生 A",
          avatar_url: null,
          status: "active",
          created_at: "2026-07-09T12:00:00+00:00",
        },
      },
      meta: { request_id: "req_1" },
    }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
}

describe("auth api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("logs in with backend username contract and stores token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(authResponse("token-login"));
    vi.stubGlobal("fetch", fetchMock);

    const response = await login({
      username: "student@example.com",
      password: "password123",
    });

    expect(response.user.username).toBe("student@example.com");
    expect(getSessionToken()).toBe("token-login");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/login",
      expect.objectContaining({
        body: JSON.stringify({
          username: "student@example.com",
          password: "password123",
        }),
      }),
    );
  });

  it("registers with backend nickname contract and stores token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(authResponse("token-register"));
    vi.stubGlobal("fetch", fetchMock);

    await register({
      username: "student@example.com",
      password: "password123",
      nickname: "学生 A",
    });

    expect(getSessionToken()).toBe("token-register");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/register",
      expect.objectContaining({
        body: JSON.stringify({
          username: "student@example.com",
          password: "password123",
          nickname: "学生 A",
        }),
      }),
    );
  });
});
