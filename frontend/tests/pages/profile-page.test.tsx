import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { setSessionToken } from "../../src/features/auth/session";
import { ProfilePage } from "../../src/pages/ProfilePage";

function jsonResponse(data: unknown, requestId = "req_profile") {
  return Promise.resolve(
    new Response(JSON.stringify({ data, meta: { request_id: requestId } }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function renderProfilePage() {
  render(
    <MantineProvider>
      <MemoryRouter initialEntries={["/profile"]}>
        <Routes>
          <Route element={<ProfilePage />} path="/profile" />
          <Route element={<div>已退出登录</div>} path="/welcome" />
        </Routes>
      </MemoryRouter>
    </MantineProvider>,
  );
}

describe("ProfilePage", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 6, 14, 12));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("loads account information and checkin colors from the real endpoints", async () => {
    setSessionToken("token-profile");
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/v1/auth/me") {
        return jsonResponse({
          id: "usr_123",
          username: "student@example.com",
          nickname: "林同学",
          avatar_url: null,
          status: "active",
          created_at: "2026-07-01T08:00:00+08:00",
        }, "req_me");
      }
      if (url === "/api/v1/checkins/2026-07-14") {
        return jsonResponse({
          id: "chk_today",
          checkin_date: "2026-07-14",
          total_subtask_count: 4,
          completed_subtask_count: 3,
          completion_ratio: "0.7500",
          color_level: 3,
          has_tasks: true,
          created_at: "2026-07-14T09:00:00+08:00",
          updated_at: "2026-07-14T10:00:00+08:00",
        }, "req_today");
      }
      if (url === "/api/v1/checkins?start_date=2026-01-01&end_date=2026-12-31") {
        return jsonResponse({
          start_date: "2026-01-01",
          end_date: "2026-12-31",
          items: [
            {
              id: "chk_13",
              checkin_date: "2026-07-13",
              total_subtask_count: 2,
              completed_subtask_count: 1,
              completion_ratio: "0.5000",
              color_level: 3,
              has_tasks: true,
              created_at: null,
              updated_at: null,
            },
            {
              id: "chk_14",
              checkin_date: "2026-07-14",
              total_subtask_count: 4,
              completed_subtask_count: 3,
              completion_ratio: "0.7500",
              color_level: 3,
              has_tasks: true,
              created_at: null,
              updated_at: null,
            },
          ],
          summary: {
            task_days: 2,
            completed_days: 2,
            current_streak_days: 2,
            longest_streak_days: 2,
          },
        }, "req_range");
      }

      return jsonResponse({}, "req_fallback");
    });
    vi.stubGlobal("fetch", fetchMock);

    renderProfilePage();

    expect(await screen.findByRole("heading", { name: "个人中心" })).toBeInTheDocument();
    expect(screen.getByText("林同学")).toBeInTheDocument();
    expect(screen.getByText("student@example.com")).toBeInTheDocument();
    expect(screen.getByText("今日完成 3/4")).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText("连续 2 天")).toBeInTheDocument();
    expect(screen.getByLabelText("2026-07-14 打卡颜色等级 3")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/checkins/2026-07-14",
      expect.objectContaining({ method: "GET" }),
    );
    expect(screen.getByLabelText("2026-12-31 打卡颜色等级 0")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/checkins?start_date=2026-01-01&end_date=2026-12-31",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("logs out from the profile page and returns to the public entry", async () => {
    setSessionToken("token-profile");
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/v1/auth/logout" && init?.method === "POST") {
        return jsonResponse({ logged_out: true }, "req_logout");
      }
      if (url === "/api/v1/auth/me") {
        return jsonResponse({
          id: "usr_123",
          username: "student@example.com",
          nickname: "林同学",
          avatar_url: null,
          status: "active",
          created_at: "2026-07-01T08:00:00+08:00",
        }, "req_me");
      }
      if (url.startsWith("/api/v1/checkins")) {
        return jsonResponse({
          checkin_date: "2026-07-14",
          total_subtask_count: 0,
          completed_subtask_count: 0,
          completion_ratio: "0.0000",
          color_level: 0,
          has_tasks: false,
        }, "req_checkin");
      }

      return jsonResponse({}, "req_fallback");
    });
    vi.stubGlobal("fetch", fetchMock);

    renderProfilePage();

    expect(await screen.findByText("林同学")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "退出登录" }));

    expect(await screen.findByText("已退出登录")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/logout",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
