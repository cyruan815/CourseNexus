import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getSessionToken, setSessionToken } from "../../src/features/auth/session";
import { ProfilePage } from "../../src/pages/ProfilePage";

function jsonResponse(data: unknown, requestId = "req_profile") {
  return Promise.resolve(
    new Response(JSON.stringify({ data, meta: { request_id: requestId } }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function errorResponse(code: string, message: string, status = 403) {
  return Promise.resolve(
    new Response(
      JSON.stringify({ error: { code, message, details: {} }, meta: { request_id: "req_error" } }),
      { status, headers: { "Content-Type": "application/json" } },
    ),
  );
}

const currentUser = {
  id: "usr_123",
  username: "student@example.com",
  nickname: "林同学",
  avatar_url: null,
  status: "active",
  created_at: "2026-07-01T08:00:00+08:00",
};

const emptyCheckin = {
  checkin_date: "2026-07-14",
  total_subtask_count: 0,
  completed_subtask_count: 0,
  completion_ratio: "0.0000",
  color_level: 0,
  has_tasks: false,
};

function renderProfilePage() {
  render(
    <MantineProvider>
      <MemoryRouter initialEntries={["/profile"]}>
        <Routes>
          <Route element={<ProfilePage />} path="/profile" />
          <Route element={<div>已退出登录</div>} path="/welcome" />
          <Route element={<div>登录页</div>} path="/login" />
        </Routes>
      </MemoryRouter>
    </MantineProvider>,
  );
}

async function openChangePasswordModal() {
  fireEvent.click(await screen.findByRole("button", { name: "修改密码" }));
  expect(await screen.findByRole("dialog", { name: "修改密码" })).toBeInTheDocument();
}

async function fillChangePasswordForm(current: string, next: string, confirm: string) {
  fireEvent.change(screen.getByLabelText(/^当前密码/), { target: { value: current } });
  fireEvent.change(screen.getByLabelText(/^新密码/), { target: { value: next } });
  fireEvent.change(screen.getByLabelText(/^确认新密码/), { target: { value: confirm } });
  fireEvent.click(screen.getByRole("button", { name: "确认修改" }));
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

  it("changes the password, clears the session and returns to the login page", async () => {
    setSessionToken("token-profile");
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/v1/auth/change-password" && init?.method === "POST") {
        return jsonResponse({ password_changed: true, relogin_required: true }, "req_change");
      }
      if (url === "/api/v1/auth/me") {
        return jsonResponse(currentUser, "req_me");
      }
      if (url.startsWith("/api/v1/checkins")) {
        return jsonResponse(emptyCheckin, "req_checkin");
      }
      return jsonResponse({}, "req_fallback");
    });
    vi.stubGlobal("fetch", fetchMock);

    renderProfilePage();

    await openChangePasswordModal();
    await fillChangePasswordForm("password123", "new-password456", "new-password456");

    expect(await screen.findByText("密码已修改，当前登录已全部失效，请使用新密码重新登录。")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/change-password",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ current_password: "password123", new_password: "new-password456" }),
      }),
    );

    fireEvent.click(screen.getByRole("button", { name: "重新登录" }));

    expect(await screen.findByText("登录页")).toBeInTheDocument();
    expect(getSessionToken()).toBeNull();
  });

  it("keeps the session when the current password is wrong", async () => {
    setSessionToken("token-profile");
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/v1/auth/change-password" && init?.method === "POST") {
        return errorResponse("CURRENT_PASSWORD_MISMATCH", "当前密码不正确");
      }
      if (url === "/api/v1/auth/me") {
        return jsonResponse(currentUser, "req_me");
      }
      if (url.startsWith("/api/v1/checkins")) {
        return jsonResponse(emptyCheckin, "req_checkin");
      }
      return jsonResponse({}, "req_fallback");
    });
    vi.stubGlobal("fetch", fetchMock);

    renderProfilePage();

    await openChangePasswordModal();
    await fillChangePasswordForm("wrong-password", "new-password456", "new-password456");

    expect(await screen.findByText("当前密码不正确")).toBeInTheDocument();
    expect(screen.queryByText(/密码已修改/)).not.toBeInTheDocument();
    expect(getSessionToken()).toBe("token-profile");
  });

  it("validates change-password inputs before calling the endpoint", async () => {
    setSessionToken("token-profile");
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/v1/auth/me") {
        return jsonResponse(currentUser, "req_me");
      }
      if (url.startsWith("/api/v1/checkins")) {
        return jsonResponse(emptyCheckin, "req_checkin");
      }
      return jsonResponse({}, "req_fallback");
    });
    vi.stubGlobal("fetch", fetchMock);

    renderProfilePage();

    await openChangePasswordModal();
    await fillChangePasswordForm("", "", "");

    expect(await screen.findByText("请填写全部密码字段")).toBeInTheDocument();

    await fillChangePasswordForm("password123", "new-password456", "different-789");

    expect(await screen.findByText("两次输入的新密码不一致")).toBeInTheDocument();

    await fillChangePasswordForm("password123", "short", "short");

    expect(await screen.findByText("新密码长度至少 8 位")).toBeInTheDocument();

    await fillChangePasswordForm("password123", "password123", "password123");

    expect(await screen.findByText("新密码不能与当前密码相同")).toBeInTheDocument();

    expect(fetchMock).not.toHaveBeenCalledWith(
      "/api/v1/auth/change-password",
      expect.anything(),
    );
    expect(getSessionToken()).toBe("token-profile");
  });
});
