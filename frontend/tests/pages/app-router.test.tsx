import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { setSessionToken } from "../../src/features/auth/session";
import { AppRouter } from "../../src/router/AppRouter";

function renderRouter() {
  render(
    <MantineProvider>
      <AppRouter />
    </MantineProvider>,
  );
}

describe("AppRouter", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
    window.history.pushState({}, "", "/");
  });

  it("redirects anonymous users to login", () => {
    window.history.pushState({}, "", "/");

    renderRouter();

    expect(screen.getByRole("heading", { name: /课枢 CourseNexus/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "开始" })).toHaveAttribute("href", "/login");
  });

  it("renders home for authenticated users", async () => {
    setSessionToken("token-123");
    window.history.pushState({}, "", "/");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            data: [
              {
                id: "crs_network",
                user_id: "usr_123",
                name: "计算机网络",
                description: "网络协议复习",
                teacher: "王老师",
                term: "2025-2026 春",
                status: "active",
                created_at: "2026-07-09T12:00:00+00:00",
                updated_at: "2026-07-09T12:00:00+00:00",
                deleted_at: null,
              },
            ],
            meta: { request_id: "req_courses" },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    renderRouter();

    expect(screen.getByRole("heading", { name: "课枢 CourseNexus" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "课程概览" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "计算机网络" })).toHaveAttribute("href", "/courses/crs_network");
  });

  it("keeps login page public", () => {
    window.history.pushState({}, "", "/login");

    renderRouter();

    expect(screen.getByRole("heading", { name: "登录 CourseNexus" })).toBeInTheDocument();
  });

  it("keeps register page public", () => {
    window.history.pushState({}, "", "/register");

    renderRouter();

    expect(screen.getByRole("heading", { name: "注册 CourseNexus" })).toBeInTheDocument();
  });

  it("renders protected course detail route for authenticated users", async () => {
    setSessionToken("token-123");
    window.history.pushState({}, "", "/courses/crs_123");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            data: {
              id: "crs_123",
              user_id: "usr_123",
              name: "高等数学",
              description: "期末复习",
              teacher: "王老师",
              term: "2026 Spring",
              status: "active",
              created_at: "2026-07-09T12:00:00+00:00",
              updated_at: "2026-07-09T12:00:00+00:00",
              deleted_at: null,
            },
            meta: { request_id: "req_1" },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    renderRouter();

    expect(await screen.findByRole("heading", { name: "高等数学" })).toBeInTheDocument();
  });
});
