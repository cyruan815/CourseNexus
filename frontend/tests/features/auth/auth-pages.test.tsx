import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LoginPage } from "../../../src/pages/LoginPage";
import { RegisterPage } from "../../../src/pages/RegisterPage";
import { getSessionToken } from "../../../src/features/auth/session";

function authResponse(token: string) {
  return new Response(
    JSON.stringify({
      data: {
        access_token: token,
        token_type: "bearer",
        expires_at: "2026-07-11T12:00:00+00:00",
        user: {
          id: "usr_123",
          username: "student@example.com",
          nickname: "学生 A",
          avatar_url: null,
          status: "active",
          created_at: "2026-07-11T12:00:00+00:00",
        },
      },
      meta: { request_id: "req_1" },
    }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
}

function apiError(message: string) {
  return new Response(
    JSON.stringify({
      error: { code: "AUTH_FAILED", message, details: {} },
      meta: { request_id: "req_error" },
    }),
    { status: 401, headers: { "Content-Type": "application/json" } },
  );
}

function renderAuthPage(page: "login" | "register") {
  render(
    <MantineProvider>
      <MemoryRouter initialEntries={[`/${page}`]}>
        <Routes>
          <Route element={<LoginPage />} path="/login" />
          <Route element={<RegisterPage />} path="/register" />
          <Route element={<h1>系统首页</h1>} path="/" />
        </Routes>
      </MemoryRouter>
    </MantineProvider>,
  );
}

describe("auth pages", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("logs in with the real auth API adapter and navigates home", async () => {
    const fetchMock = vi.fn().mockResolvedValue(authResponse("token-login"));
    vi.stubGlobal("fetch", fetchMock);

    renderAuthPage("login");

    fireEvent.change(screen.getByLabelText(/用户名\/邮箱/), {
      target: { value: "student@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/密码/), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: "登录" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "系统首页" })).toBeInTheDocument());
    expect(getSessionToken()).toBe("token-login");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/login",
      expect.objectContaining({
        body: JSON.stringify({ username: "student@example.com", password: "password123" }),
      }),
    );
  });

  it("registers with the real auth API adapter and navigates home", async () => {
    const fetchMock = vi.fn().mockResolvedValue(authResponse("token-register"));
    vi.stubGlobal("fetch", fetchMock);

    renderAuthPage("register");

    fireEvent.change(screen.getByLabelText("昵称"), { target: { value: "学生 A" } });
    fireEvent.change(screen.getByLabelText(/用户名\/邮箱/), {
      target: { value: "student@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/密码/), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: "注册" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "系统首页" })).toBeInTheDocument());
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

  it("shows backend auth errors without navigating away", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(apiError("账号或密码不正确")));

    renderAuthPage("login");

    fireEvent.change(screen.getByLabelText(/用户名\/邮箱/), {
      target: { value: "student@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/密码/), { target: { value: "bad-password" } });
    fireEvent.click(screen.getByRole("button", { name: "登录" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("账号或密码不正确");
    expect(screen.getByRole("heading", { name: "登录 CourseNexus" })).toBeInTheDocument();
  });
});
